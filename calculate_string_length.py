import sys, os, warnings, hashlib
from typing import Literal, Tuple, List



# region 计算字符打印宽度
def Cut_And_Pad_String(string:str, length:int=30, cut_align:str='left', pad_align:str='right', pad_char:str=' ') -> str:
    """
    This function cuts a string to a certain length and pads it with spaces if necessary.
    """
    if Calc_String_Width(string) > length:
        while Calc_String_Width(string) > length:
            if cut_align == 'left':
                string = string[1:]
            elif cut_align == 'right':
                string = string[:-1]
        return string
    elif Calc_String_Width(string) < length:
        while Calc_String_Width(string) < length:
            if pad_align == 'left':
                string = pad_char + string
            elif pad_align == 'right':
                string = string + pad_char
        return string
    else:
        return string

def Calc_String_Width(text:str|bytes, start_offs:int=0, end_offs:int=None) -> int:
    """
    Return the screen column width of text between start_offs and end_offs.

    text may be unicode or a byte string in the target _byte_encoding

    Some characters are wide (take two columns) and others affect the
    previous character (take zero columns).  Use the widths table above
    to calculate the screen column width of text[start_offs:end_offs]
    """
    if not text:
        return 0
    _byte_encoding: Literal["utf8", "narrow", "wide"] = "narrow"
    if end_offs is None:
        end_offs = len(text)
    if start_offs > end_offs:
        raise ValueError((start_offs, end_offs))
    if isinstance(text, str):
        return sum(Calc_Char_Width(char) for char in text[start_offs:end_offs])
    if _byte_encoding == "utf8":
        try:
            return sum(Calc_Char_Width(char) for char in text[start_offs:end_offs].decode("utf-8"))
        except UnicodeDecodeError as exc:
            warnings.warn(
                "`calc_width` with text encoded to bytes can produce incorrect results"
                f"due to possible offset in the middle of character: {exc}",
                UnicodeWarning,
                stacklevel=2,
            )
        i = start_offs
        sc = 0
        while i < end_offs:
            o, i = _decode_one(text, i)
            w = Calc_Char_Width(chr(o))
            sc += w
        return sc
    return end_offs - start_offs

def Calc_Char_Width(char:str) -> Literal[0, 1, 2]:
    """
    Calculate the width of a character.
    """
    if char in ['‘', '’', '“', '”', '…', '·', '—'
                , '《' , '》', '↑', '↓', '←', '→']:
        return 2
    width = _wcwidth(char)
    if width < 0:
        return 0
    return width

def _decode_one(text: bytes | str, pos: int) -> Tuple[int, int]:
    """
    Return (ordinal at pos, next position) for UTF-8 encoded text.
    """
    lt = len(text) - pos
    b2 = 0  
    b3 = 0  
    b4 = 0  
    try:
        if isinstance(text, str):
            b1 = ord(text[pos])
            if lt > 1:
                b2 = ord(text[pos + 1])
            if lt > 2:
                b3 = ord(text[pos + 2])
            if lt > 3:
                b4 = ord(text[pos + 3])
        else:
            b1 = text[pos]
            if lt > 1:
                b2 = text[pos + 1]
            if lt > 2:
                b3 = text[pos + 2]
            if lt > 3:
                b4 = text[pos + 3]
    except Exception as e:
        raise ValueError(f"{e}: text={text!r}, pos={pos!r}, lt={lt!r}").with_traceback(e.__traceback__) from e
    if not b1 & 0x80:
        return b1, pos + 1
    error = ord("?"), pos + 1
    if lt < 2:
        return error
    if b1 & 0xE0 == 0xC0:
        if b2 & 0xC0 != 0x80:
            return error
        o = ((b1 & 0x1F) << 6) | (b2 & 0x3F)
        if o < 0x80:
            return error
        return o, pos + 2
    if lt < 3:
        return error
    if b1 & 0xF0 == 0xE0:
        if b2 & 0xC0 != 0x80:
            return error
        if b3 & 0xC0 != 0x80:
            return error
        o = ((b1 & 0x0F) << 12) | ((b2 & 0x3F) << 6) | (b3 & 0x3F)
        if o < 0x800:
            return error
        return o, pos + 3
    if lt < 4:
        return error
    if b1 & 0xF8 == 0xF0:
        if b2 & 0xC0 != 0x80:
            return error
        if b3 & 0xC0 != 0x80:
            return error
        if b4 & 0xC0 != 0x80:
            return error
        o = ((b1 & 0x07) << 18) | ((b2 & 0x3F) << 12) | ((b3 & 0x3F) << 6) | (b4 & 0x3F)
        if o < 0x10000:
            return error
        return o, pos + 4
    return error

def _wcwidth(wc, unicode_version='auto'):
    from calculate_string_length_const import WIDE_EASTASIAN, ZERO_WIDTH, ZERO_WIDTH_CF
    ucs = ord(wc)
    if ucs in ZERO_WIDTH_CF:
        return 0
    if ucs < 32 or 0x07F <= ucs < 0x0A0:
        return -1
    _unicode_version = _wcmatch_version(unicode_version)
    if _bisearch(ucs, ZERO_WIDTH[_unicode_version]):
        return 0
    return 1 + _bisearch(ucs, WIDE_EASTASIAN[_unicode_version])

def _bisearch(ucs, table):
    """
    Auxiliary function for binary search in interval table.

    :arg int ucs: Ordinal value of unicode character.
    :arg list table: List of starting and ending ranges of ordinal values,
        in form of ``[(start, end), ...]``.
    :rtype: int
    :returns: 1 if ordinal value ucs is found within lookup table, else 0.
    """
    lbound = 0
    ubound = len(table) - 1
    if ucs < table[0][0] or ucs > table[ubound][1]:
        return 0
    while ubound >= lbound:
        mid = (lbound + ubound) // 2
        if ucs > table[mid][1]:
            lbound = mid + 1
        elif ucs < table[mid][0]:
            ubound = mid - 1
        else:
            return 1
    return 0

def _wcversion_value(ver_string):
    retval = tuple(map(int, (ver_string.split('.'))))
    return retval

def _wcmatch_version(given_version):
    from calculate_string_length_const import UNICODE_VERSIONS
    _PY3 = (sys.version_info[0] >= 3)
    _return_str = not _PY3 and isinstance(given_version, str)
    if _return_str:
        unicode_versions = [ucs.encode() for ucs in UNICODE_VERSIONS]
    else:
        unicode_versions = UNICODE_VERSIONS
    latest_version = unicode_versions[-1]
    if given_version in (u'auto', 'auto'):
        given_version = os.environ.get(
            'UNICODE_VERSION',
            'latest' if not _return_str else latest_version.encode())
    if given_version in (u'latest', 'latest'):
        return latest_version if not _return_str else latest_version.encode()
    if given_version in unicode_versions:
        return given_version if not _return_str else given_version.encode()
    try:
        cmp_given = _wcversion_value(given_version)
    except ValueError:
        warnings.warn("UNICODE_VERSION value, {given_version!r}, is invalid. "
                      "Value should be in form of `integer[.]+', the latest "
                      "supported unicode version {latest_version!r} has been "
                      "inferred.".format(given_version=given_version,
                                         latest_version=latest_version))
        return latest_version if not _return_str else latest_version.encode()
    earliest_version = unicode_versions[0]
    cmp_earliest_version = _wcversion_value(earliest_version)
    if cmp_given <= cmp_earliest_version:
        warnings.warn("UNICODE_VERSION value, {given_version!r}, is lower "
                      "than any available unicode version. Returning lowest "
                      "version level, {earliest_version!r}".format(
                          given_version=given_version,
                          earliest_version=earliest_version))
        return earliest_version if not _return_str else earliest_version.encode()
    for idx, unicode_version in enumerate(unicode_versions):
        try:
            cmp_next_version = _wcversion_value(unicode_versions[idx + 1])
        except IndexError:
            return latest_version if not _return_str else latest_version.encode()
        if cmp_given == cmp_next_version[:len(cmp_given)]:
            return unicode_versions[idx + 1]
        if cmp_next_version > cmp_given:
            return unicode_version
    assert False, ("Code path unreachable", given_version, unicode_versions)
# endregion