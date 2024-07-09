import pendulum
from airflow.decorators import dag, task


@dag(
    schedule='@daily',
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    tags=["mock"],
)
def mock_pipeline():
    @task()
    def extract():
        # here is your code
        return 1

    @task()
    def transform(data):
        # here is your code again
        return data + 1

    @task()
    def load(data):
        # here is your code one more time
        return data + 1

    # defining tasks dependecies
    data = extract()
    transformed_data = transform(data)
    load(transformed_data)


# Achtung! execution
mock_pipeline()
