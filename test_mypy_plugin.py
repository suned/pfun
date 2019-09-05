from pfun import io, Immutable
from typing import Tuple


def transform(s: str) -> int:
    pass


class DataSet(Immutable):
    pass


class Model(Immutable):
    pass


class Metrics(Immutable):
    precision: float
    recall: float


@io.io
def read_csv(path: str) -> DataSet:
    pass


@io.io
def preprocess(data: DataSet) -> DataSet:
    pass


@io.io
def split(data: DataSet) -> Tuple[DataSet, DataSet]:
    pass


@io.io
def train(data: Tuple[DataSet, DataSet]) -> Tuple[Model, DataSet, DataSet]:
    pass


@io.io
def evaluate(data: Tuple[Model, DataSet, DataSet]) -> Metrics:
    pass


@io.io
def report(metrics: Metrics) -> Metrics:
    pass


reveal_type(
    read_csv('data.csv').and_then(preprocess).and_then(train).and_then(
        evaluate).and_then(report))
