from regast.core.declarations.comment import Comment
from regast.core.declarations.contracts.contract import Contract, InheritanceSpecifier
from regast.core.declarations.contracts.interface import Interface
from regast.core.declarations.contracts.library import Library
from regast.core.declarations.functions.fallback_function import FallbackFunction
from regast.core.declarations.functions.receive_function import ReceiveFunction
from regast.core.declarations.source_unit import SourceUnit
from regast.exceptions import ParsingException
from regast.parsing.expressions import ExpressionParser
from regast.parsing.tree_sitter_node import TreeSitterNode
from regast.parsing.types import TypeParser
from regast.parsing.variables import VariableParser


class DeclarationParser:
    @staticmethod
    def parse_source_unit(node: TreeSitterNode, fname: str):
        assert node.type == 'source_file'

        source_unit = SourceUnit(node, fname)
        for child_node in node.children:
            # Directives
            if child_node.type == 'pragma_directive':
                pragma_directive = DeclarationParser.parse_pragma_directive(child_node)
                source_unit._pragma_directives.append(pragma_directive)
                
            elif child_node.type == 'import_directive':
                import_directive = DeclarationParser.parse_import_directive(child_node)
                source_unit._import_directives.append(import_directive)

            # Contracts
            elif child_node.type in ['contract_declaration', 'interface_declaration', 'library_declaration']:
                contract = DeclarationParser.parse_contract_interface_library_declaration(child_node)
                if isinstance(contract, Contract):
                    source_unit._contracts.append(contract)
                elif isinstance(contract, Interface):
                    source_unit._interfaces.append(contract)
                else:
                    assert isinstance(contract, Library)
                    source_unit._libraries.append(contract)
                
            # Declarations
            elif child_node.type == 'error_declaration':
                custom_error = DeclarationParser.parse_error_declaration(child_node)
                source_unit._custom_errors.append(custom_error)
                
            elif child_node.type == 'struct_declaration':
                struct = DeclarationParser.parse_struct_declaration(child_node)
                source_unit._structs.append(struct)
                
            elif child_node.type == 'enum_declaration':
                enum = DeclarationParser.parse_enum_declaration(child_node)
                source_unit._enums.append(enum)

            elif child_node.type == 'function_definition':
                function = DeclarationParser.parse_function_definition(child_node)
                source_unit._functions.append(function)

            elif child_node.type == 'constant_variable_declaration':
                constant = VariableParser.parse_constant_variable_declaration(child_node)
                source_unit._constants.append(constant)

            elif child_node.type == 'user_defined_type_definition':
                type_definition = DeclarationParser.parse_user_defined_type_definition(child_node)
                source_unit._type_definitions.append(type_definition)

            else:
                raise ParsingException(f'Unknown tree-sitter node for source_unit: {child_node.type}')
        
        return source_unit

    # CONTRACTS
    @staticmethod
    def parse_contract_interface_library_declaration(node: TreeSitterNode):
        assert node.type in ['contract_declaration', 'interface_declaration', 'library_declaration']

        contract = None
        if node.type == 'contract_declaration':
            contract = Contract(node)
        elif node.type == 'interface_declaration':
            contract = Interface(node)
        elif node.type == 'library_declaration':
            contract = Library(node)

        def parse_inheritance_specifier(node: TreeSitterNode):
            assert node.type == 'inheritance_specifier'

            ancestor, *ancestor_arguments = node.children
            call_arguments = []
            if ancestor_arguments:
                for child_node in ancestor_arguments:
                    if child_node.type == 'call_argument':
                        call_arguments.append(child_node)
                    elif child_node.type not in ['(', ')', ',']:
                        raise ParsingException(f'Unknown tree-sitter node type for _call_arguments: {child_node.type}')
            
            inheritance_specifier = InheritanceSpecifier(node)
            inheritance_specifier._name = TypeParser.parse_user_defined_type(ancestor)
            for call_argument in call_arguments:
                if len(call_argument.children) == 1:
                    expression = ExpressionParser.parse_expression(call_argument)
                    inheritance_specifier.arguments.append(expression)
                else:
                    assert len(call_arguments) == 1
                    struct_arguments = ExpressionParser.parse_struct_arguments(call_argument)
                    inheritance_specifier._struct_arguments = struct_arguments

            contract._inheritance_specifiers.append(inheritance_specifier)

        def parse_contract_body(node: TreeSitterNode):
            assert node.type == 'contract_body'

            for child_node in node.children:
                if child_node.type == 'function_definition':
                    function = DeclarationParser.parse_function_definition(child_node)
                    contract._functions.append(function)

                elif child_node.type == 'modifier_definition':
                    modifier = DeclarationParser.parse_modifier_definition(child_node)
                    contract._modifiers.append(modifier)

                elif child_node.type == 'error_declaration':
                    custom_error = DeclarationParser.parse_error_declaration(child_node)
                    contract._custom_errors.append(custom_error)

                elif child_node.type == 'state_variable_declaration':
                    state_variable = VariableParser.parse_state_variable_declaration(child_node)
                    contract._state_variables.append(state_variable)
                    
                elif child_node.type == 'struct_declaration':
                    struct = DeclarationParser.parse_struct_declaration(child_node)
                    contract._structs.append(struct)
                    
                elif child_node.type == 'enum_declaration':
                    enum = DeclarationParser.parse_enum_declaration(child_node)
                    contract._enums.append(enum)

                elif child_node.type == 'event_definition':
                    event = DeclarationParser.parse_event_definition(child_node)
                    contract._events.append(event)
                    
                elif child_node.type == 'using_directive':
                    using_directive = DeclarationParser.parse_using_directive(child_node)
                    contract._using_directives.append(using_directive)
                    
                elif child_node.type == 'constructor_definition':
                    assert not contract.constructor
                    contract._constructor = DeclarationParser.parse_constructor_definition(child_node)
                    
                elif child_node.type == 'fallback_receive_definition':
                    f = DeclarationParser.parse_fallback_receive_definition(child_node)
                    if isinstance(f, FallbackFunction):
                        assert not contract.fallback_function
                        contract._fallback_function = f
                    elif isinstance(f, ReceiveFunction):
                        assert not contract.receive_function
                        contract._receive_function = f
                    else:
                        # TODO Implement fallback_receive_definition and uncomment this exception
                        pass
                        # raise ParsingException(f'Unknown fallback_receive_definition: {child_node}')
                        
                elif child_node.type == 'user_defined_type_definition':
                    type_definition = DeclarationParser.parse_user_defined_type_definition(child_node)
                    contract._type_definitions.append(type_definition)

                elif child_node.type not in ['{', '}']:
                    raise ParsingException(f'Unknown tree-sitter node type for contract member: {child_node.type}')

        for child_node in node.children:
            if child_node.type == 'abstract':
                contract._abstract = True
                
            elif child_node.type == 'identifier':
                contract._name = ExpressionParser.parse_identifier(child_node)
                
            elif child_node.type == 'inheritance_specifier':
                parse_inheritance_specifier(child_node)
                
            elif child_node.type == 'contract_body':
                parse_contract_body(child_node)

            elif child_node.type not in ['contract', 'interface', 'library', 'is', ',']:
                raise ParsingException(f'Unknown tree-sitter node for contract_declaration: {child_node.type}')

        return contract

    # DIRECTIVES
    @staticmethod
    def parse_import_directive(node):
        assert node.type == 'import_directive'

        # TODO Stopped here

    @staticmethod
    def parse_pragma_directive(node):
        pass

    @staticmethod
    def parse_using_directive(node):
        pass

    # FUNCTIONS
    @staticmethod
    def parse_constructor_definition(node):
        pass

    @staticmethod
    def parse_fallback_receive_definition(node):
        pass

    @staticmethod
    def parse_modifier_definition(node):
        pass

    @staticmethod
    def parse_function_definition(node):
        pass

    # OTHERS
    @staticmethod
    def parse_error_declaration(node):
        pass

    @staticmethod
    def parse_enum_declaration(node):
        pass
    
    @staticmethod
    def parse_struct_declaration(node):
        pass

    @staticmethod
    def parse_event_definition(node):
        pass

    @staticmethod
    def parse_user_defined_type_definition(node):
        pass