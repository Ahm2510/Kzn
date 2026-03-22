import pandas as pd

from app.services.preprocessing import preprocess_with_options
from app.services.transformation import transform_dataset
from app.services.insight_engine.engine import InsightEngine
from app.schemas.insight.cleaning import CleaningOptions
from app.schemas.insight.report import InsightReport


class InsightV15Service:
    def __init__(self):
        self.engine = InsightEngine()

    def run(
        self,
        current_df: pd.DataFrame,
        baseline_df: pd.DataFrame | None,
        cleaning: CleaningOptions,
    ) -> InsightReport:

        # Preprocess current dataset
        current_df = preprocess_with_options(current_df, cleaning)
        
        # Validate current dataset is not empty after cleaning
        if current_df.empty:
            raise ValueError(
                "After applying data cleaning options, the current dataset has no remaining rows. "
                "Please adjust your cleaning options or check your data."
            )
        
        current_df = transform_dataset(current_df)

        # Preprocess baseline dataset if provided
        if baseline_df is not None:
            baseline_df = preprocess_with_options(baseline_df, cleaning)
            
            # Validate baseline dataset is not empty after cleaning
            if baseline_df.empty:
                raise ValueError(
                    "After applying data cleaning options, the baseline dataset has no remaining rows. "
                    "Please adjust your cleaning options or check your baseline data."
                )
            
            baseline_df = transform_dataset(baseline_df)

        return self.engine.run(
            current_df=current_df,
            baseline_df=baseline_df,
        )
