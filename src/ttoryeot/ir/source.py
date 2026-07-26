from pydantic import BaseModel, model_validator


class SourceRange(BaseModel):
    file: str
    start_line: int  # 1-based
    start_col: int   # 1-based
    end_line: int
    end_col: int
    start_offset: int  # 파일 내 0-based 문자 오프셋
    end_offset: int

    @model_validator(mode="after")
    def _ordered(self) -> "SourceRange":
        if self.start_offset < 0 or self.end_offset < self.start_offset:
            raise ValueError("invalid offset range")
        return self
