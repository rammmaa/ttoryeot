import hashlib
import re

from kiwipiepy import Kiwi

from ttoryeot.ir.models import (
    Block,
    DocumentIR,
    NounPhrase,
    ReferenceExpression,
    SentenceIR,
    Token,
)
from ttoryeot.ir.source import SourceRange
from ttoryeot.parsing.markdown import parse_blocks

NOUN_TAGS = {"NNG", "NNP", "SL"}

# 지시어 판별 규칙은 실제 kiwipiepy(0.23.2) 형태소 분석 결과를 probe로 검증한
# 뒤 정했다 (probe: split_into_sents(text, return_tokens=True)의 t.start/t.len은
# 문장이 아니라 kiwi에 넘긴 전체 텍스트 기준 오프셋이다 — sent.start를 더하면
# 왕복 불변식이 깨진다). 지시어는 Kiwi 분석 결과상 두 갈래로 나뉜다:
#   - FUSED: "해당"/"위"는 항상 NNG로 분석되고, 뒤따르는 명사와 (공백만 사이에
#     두고) 곧바로 이어지는 별개 토큰이므로 연속 NNG|NNP|SL 명사구 병합 규칙에
#     자연히 흡수된다 → 병합된 런의 첫 토큰이 이 표면형이면 지시어로 인정한다.
#   - "동일한"은 "동일"(NNG) + "하"(XSA) + "ᆫ"(ETM) 세 형태소로 분리되고 XSA/ETM은
#     명사 태그가 아니므로 명사구 런에 병합되지 않는다 → 별도 패턴(NNG 뒤에
#     XSA+ETM이 곧바로 붙는 경우)으로 인식한다.
#   - DETERMINER: "이"/"그"는 관형사(MM)일 때만 지시어이다. 조사 '이'(예:
#     "값이" → JKS)·대명사 '그'(예: "그가" → NP)와 표면형이 겹치므로 태그로
#     반드시 구분해야 하며, 관형사 뒤에 명사가 바로 와야 한다 (브리프의
#     "조사 '이'와 구분" 요구사항).
FUSED_DEMONSTRATIVES = {"해당", "위"}
DETERMINER_DEMONSTRATIVES = {"이", "그"}
_DETERMINER_TAGS = {"MM", "MMD"}


_INLINE_CODE = re.compile(r"``.+?``|`[^`\n]+`")


def _mask_inline_code(text: str) -> str:
    """인라인 코드 스팬을 같은 길이의 공백으로 바꿔 Kiwi 입력에서만 제외한다
    (스펙 §5). 길이가 보존되므로 토큰 오프셋은 원문 기준 그대로이고, 문장 텍스트는
    여전히 원문 슬라이스에서 오므로 코드가 포함된 원문이 유지된다.
    알려진 미탐(항상 길이 안전): 3중 백틱 인라인 스팬(```x```)은 백틱 하나가 남고,
    소프트 줄바꿈을 걸친 스팬(`foo\\nbar`)은 마스킹되지 않는다."""
    return _INLINE_CODE.sub(lambda m: " " * len(m.group()), text)


def to_range(file: str, source: str, start: int, end: int) -> SourceRange:
    def linecol(off: int) -> tuple[int, int]:
        line = source.count("\n", 0, off) + 1
        last_nl = source.rfind("\n", 0, off)
        return line, off - (last_nl + 1) + 1

    sl, sc = linecol(start)
    el, ec = linecol(end)
    return SourceRange(
        file=file,
        start_line=sl,
        start_col=sc,
        end_line=el,
        end_col=ec,
        start_offset=start,
        end_offset=end,
    )


def _noun_runs(tokens: list[Token]) -> list[list[Token]]:
    """연속된 NNG|NNP|SL 토큰을 하나의 런으로 묶는다."""
    runs: list[list[Token]] = []
    run: list[Token] = []
    for tok in tokens + [None]:
        if tok is not None and tok.tag in NOUN_TAGS:
            run.append(tok)
            continue
        if run:
            runs.append(run)
            run = []
    return runs


def _noun_phrases(
    file: str, source: str, runs: list[list[Token]]
) -> list[NounPhrase]:
    phrases = []
    for run in runs:
        start = run[0].range.start_offset
        end = run[-1].range.end_offset
        phrases.append(
            NounPhrase(
                text=source[start:end],
                head=run[-1].form,
                range=to_range(file, source, start, end),
            )
        )
    return phrases


def _fused_references(
    runs: list[list[Token]], phrases: list[NounPhrase]
) -> list[ReferenceExpression]:
    """지시어가 그 자체로 명사구 런의 첫 토큰으로 흡수된 경우 (해당/위)."""
    refs = []
    for run, phrase in zip(runs, phrases):
        first = run[0]
        if first.form in FUSED_DEMONSTRATIVES and len(run) > 1:
            refs.append(
                ReferenceExpression(
                    text=phrase.text,
                    demonstrative=first.form,
                    head=phrase.head,
                    range=phrase.range,
                )
            )
    return refs


def _find_following_phrase(
    source: str, phrases: list[NounPhrase], after_offset: int
) -> NounPhrase | None:
    """after_offset 바로 뒤(공백만 사이에 두고)에서 시작하는 명사구를 찾는다."""
    for np in phrases:
        if np.range.start_offset >= after_offset:
            gap = source[after_offset : np.range.start_offset]
            if gap.strip() == "" and len(gap) <= 2:
                return np
            return None
    return None


def _attributive_references(
    file: str, source: str, tokens: list[Token], phrases: list[NounPhrase]
) -> list[ReferenceExpression]:
    """"동일" + XSA(하) + ETM(ᆫ) → "동일한" 뒤에 오는 명사구를 지시어로 인식한다."""
    refs = []
    for i, tok in enumerate(tokens):
        if tok.form != "동일" or tok.tag != "NNG" or i + 2 >= len(tokens):
            continue
        xsa, etm = tokens[i + 1], tokens[i + 2]
        if xsa.tag != "XSA" or etm.tag != "ETM":
            continue
        dem_end = max(xsa.range.end_offset, etm.range.end_offset)
        np = _find_following_phrase(source, phrases, dem_end)
        if np is None:
            continue
        start = tok.range.start_offset
        refs.append(
            ReferenceExpression(
                text=source[start : np.range.end_offset],
                demonstrative=source[start:dem_end],
                head=np.head,
                range=to_range(file, source, start, np.range.end_offset),
            )
        )
    return refs


def _determiner_references(
    file: str, source: str, tokens: list[Token], phrases: list[NounPhrase]
) -> list[ReferenceExpression]:
    """관형사(MM)로만 인정되는 이/그 뒤에 명사구가 바로 오는 경우."""
    refs = []
    for i, tok in enumerate(tokens):
        if tok.form not in DETERMINER_DEMONSTRATIVES:
            continue
        if tok.tag not in _DETERMINER_TAGS:
            continue
        start = tok.range.start_offset
        if start > 0 and source[start - 1].isalnum():
            # 단어 중간에서 시작한 이/MM은 미등록 외래어 오분해 아티팩트다
            # ('메모이제이션' → 메모+이제+이/MM+션). 지시 관형사는 단어 경계에서만.
            continue
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if nxt is None or nxt.tag not in NOUN_TAGS:
            continue
        np = _find_following_phrase(source, phrases, tok.range.end_offset)
        if np is None:
            continue
        start = tok.range.start_offset
        refs.append(
            ReferenceExpression(
                text=source[start : np.range.end_offset],
                demonstrative=tok.form,
                head=np.head,
                range=to_range(file, source, start, np.range.end_offset),
            )
        )
    return refs


def _references(
    file: str,
    source: str,
    tokens: list[Token],
    runs: list[list[Token]],
    phrases: list[NounPhrase],
) -> list[ReferenceExpression]:
    refs = _fused_references(runs, phrases)
    refs.extend(_attributive_references(file, source, tokens, phrases))
    refs.extend(_determiner_references(file, source, tokens, phrases))
    refs.sort(key=lambda r: r.range.start_offset)
    return refs


def lower_document(path: str, source: str, kiwi: Kiwi) -> DocumentIR:
    blocks_ir: list[Block] = []
    for raw in parse_blocks(source):
        block_range = to_range(
            path, source, raw.start_offset, raw.start_offset + len(raw.text)
        )
        if raw.kind == "code_block" or not raw.text:
            blocks_ir.append(
                Block(kind=raw.kind, level=raw.level, range=block_range, sentences=[])
            )
            continue

        sentences = []
        for sent in kiwi.split_into_sents(_mask_inline_code(raw.text), return_tokens=True):
            s_start = raw.start_offset + sent.start
            s_end = raw.start_offset + sent.end
            tokens = [
                Token(
                    form=t.form,
                    tag=t.tag,
                    range=to_range(
                        path,
                        source,
                        raw.start_offset + t.start,
                        raw.start_offset + t.start + t.len,
                    ),
                )
                for t in sent.tokens
            ]
            runs = _noun_runs(tokens)
            phrases = _noun_phrases(path, source, runs)
            sentences.append(
                SentenceIR(
                    text=source[s_start:s_end],
                    range=to_range(path, source, s_start, s_end),
                    tokens=tokens,
                    noun_phrases=phrases,
                    references=_references(path, source, tokens, runs, phrases),
                )
            )
        blocks_ir.append(
            Block(kind=raw.kind, level=raw.level, range=block_range, sentences=sentences)
        )
    return DocumentIR(
        path=path,
        content_hash=hashlib.sha256(source.encode()).hexdigest()[:16],
        blocks=blocks_ir,
    )
