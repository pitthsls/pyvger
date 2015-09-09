import re


def parse_enum(enum):
    """Parse a MARC enumeration"""

    re1 = r'((?:v|Bd|no)\.)(\d+\w?)-\1(\d+\w?):((?:no|pt|Nr)\.|issue )(\d+)$'
    match = re.match(re1, enum)
    if match:
        return {'ec1': match.group(1), 'ec2': match.group(4),
                'es1': int(match.group(2)), 'ee1': int(match.group(3)),
                'es2': int(match.group(2)), 'ee2': int(match.group(5))}

