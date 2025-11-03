from dataclasses import dataclass, asdict


@dataclass
class Config:
    my: dict[str, int]
    your: dict[str, dict[str, int]]


config = asdict(Config(
    {"mother": 1},
    {"dad": {"father": 1}}
))
