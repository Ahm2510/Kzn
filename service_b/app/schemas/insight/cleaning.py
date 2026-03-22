from pydantic import BaseModel


class CleaningOptions(BaseModel):
    drop_duplicates: bool = True
    drop_missing: bool = True
    cap_outliers: bool = False
    normalize_columns: bool = True
