from enum import Enum


class PermissionHelper:
    @staticmethod
    def both_have_perm(a: str, b: str, permission_tested: Enum):
        return permission_helper.combine_perm_bool(a[permission_tested.value], b[permission_tested.value])

    @staticmethod
    def combine_perm(a: str, b: str) -> str:
        return '1' if (a == '1' and b == '1') else '0'

    @staticmethod
    def combine_perm_bool(a: str, b: str) -> bool:
        return a == '1' and b == '1'

    @staticmethod
    def combine_masks(permission_mask_a: str, permission_mask_b: str) -> str:
        both_masks = zip(list(permission_mask_a), list(permission_mask_b))
        return ''.join(map(lambda x: permission_helper.combine_perm(x[0], x[1]), both_masks))


permission_helper = PermissionHelper()
