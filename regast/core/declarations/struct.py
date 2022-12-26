from typing import List

from regast.core.core import Core
from regast.core.expressions.identifier import Identifier
from regast.core.variables.struct_member import StructMember

class Struct(Core):
    def __init__(
        self,
        name: Identifier,
        members: List[StructMember]
    ):
        super().__init__()

        self._name: Identifier = name
        self._members: List[StructMember] = members

    @property
    def name(self) -> Identifier:
        return self._name

    @property
    def members(self) -> List[StructMember]:
        return list(self._members)

    def __eq__(self, other):
        if isinstance(other, Struct):
            return self.name == other.name and self.members == other.members
        return False