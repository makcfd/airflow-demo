import pendulum
from airflow.decorators import dag, task
import pandas as pd
import warnings
warnings.filterwarnings("ignore")


@dag(
    schedule='@once',
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    tags=["titanic"]
)
def titanic():

    from airflow.providers.postgres.hooks.postgres import PostgresHook
    from sklearn import datasets

    @task()
    def read_data() -> (pd.DataFrame, pd.Series):
        return datasets.fetch_openml(name='titanic', version=1, return_X_y=True)

    @task()
    def feature_engineering(X: pd.DataFrame) -> pd.DataFrame:
        X.drop(['ticket', 'cabin', 'body', 'boat', 'home.dest'], axis=1, inplace=True)
        X['family_size'] = X['parch'] + X['sibsp']
        X.drop(['parch', 'sibsp'], axis=1, inplace=True)
        X['is_alone'] = 1
        X['is_alone'].loc[X['family_size'] > 1] = 0
        X['title'] = X['name'].str.split(", ", expand=True)[1].str.split(".", expand=True)[0]
        X.drop(["name"], axis=1, inplace=True)
        rare_titles = (X['title'].value_counts() < 10)
        X.title.loc[X.title == 'Miss'] = 'Mrs'
        X['title'] = X.title.apply(lambda x: 'rare' if rare_titles[x] else x)
        return X

    @task()
    def create_table():
        from sqlalchemy import Table, Column, DateTime, Float, Integer, Index, MetaData, String, UniqueConstraint, \
            inspect  # noqa
        hook = PostgresHook("destination_db")
        db_engine = hook.get_sqlalchemy_engine()

        metadata = MetaData()

        churn_table = Table("clean_users_churn", metadata,
                            Column('id', Integer, primary_key=True, autoincrement=True),
                            Column('customer_id', String),
                            Column('begin_date', DateTime),
                            Column('monthly_charges', Float),
                            Column('internet_service', String),
                            Column('senior_citizen', Integer),
                            Column('target', Integer),
                            UniqueConstraint('customer_id', name='unique_clean_customer_constraint')
                            )
        if not inspect(db_engine).has_table(churn_table.name):
            metadata.create_all(db_engine)

    @task()
    def save_engineered_data(X: pd.DataFrame) -> None:
        pass

    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.model_selection import train_test_split

    @task()
    def data_transformation(X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, test_size=0.2)

        # Selecting features
        cat_features = X_train.select_dtypes(include="object")
        potential_binary_features = cat_features.nunique() == 2

        binary_cat_features = cat_features[
            potential_binary_features[potential_binary_features].index
        ]
        other_cat_features = cat_features[
            potential_binary_features[~potential_binary_features].index
        ]
        num_features = X_train.select_dtypes(["float"])

        # Defining the preprocessor
        preprocessor = ColumnTransformer(
            transformers=[
                (
                    "binary",
                    OneHotEncoder(),
                    binary_cat_features.columns.tolist(),
                ),
                (
                    "cat",
                    OneHotEncoder(),
                    other_cat_features.columns.tolist(),
                ),
                ("num", StandardScaler(), num_features.columns.tolist()),
            ],
            remainder="drop",
            verbose_feature_names_out=False,
        )

        # Fit the preprocessor on the training data and transform both the training and test data
        X_train_preprocessed = preprocessor.fit_transform(X_train)
        X_test_preprocessed = preprocessor.transform(X_test)
        return X_train_preprocessed, X_test_preprocessed, y_train, y_test

    @task()
    def extract():
        pass


titanic()
