import opencc


def convert_text(text: str) -> str:
    """
    将繁体中文文本转换为简体中文文本, 将大写字母转换为小写.
    Args:
        text (str): 文本.
    Returns:
        text_converted: 转换后文本.
    """
    text_converted = opencc.OpenCC('t2s').convert(text)
    text_converted = text_converted.lower()
    return text_converted
