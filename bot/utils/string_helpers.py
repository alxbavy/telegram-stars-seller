from enum import StrEnum


class WordCase(StrEnum):
    NOMINATIVE = "nominative"
    GENITIVE = "genitive"
    DATIVE = "dative"
    ACCUSATIVE = "accusative"
    INSTRUMENTAL = "instrumental"
    PREPOSITIONAL = "prepositional"


class EndingFor(StrEnum):
    SECONDS = "seconds"
    MINUTES = "minutes"


def get_ending_for_digit_string(digit_string: str | None, word_case: WordCase, ending_for: EndingFor = EndingFor.MINUTES) -> str:
    if not digit_string:
        return ""

    # 1 или X...X1, но не X...X11
    if digit_string == "1" or (len(digit_string) >= 2 and digit_string[-2] != "1" and digit_string[-1] == "1"):
        if word_case == WordCase.NOMINATIVE:
            ending = "а"
        elif word_case == WordCase.GENITIVE or word_case == WordCase.ACCUSATIVE:
            ending = "у"
        elif word_case == WordCase.DATIVE or word_case == WordCase.PREPOSITIONAL:
            ending = "е"
        else:  # WordCase.INSTRUMENTAL
            ending = "ой"

    else:
        if word_case == WordCase.NOMINATIVE or word_case == WordCase.GENITIVE or word_case == WordCase.ACCUSATIVE:
            # [056789] или X...X[056789] или 11, 12, 13, 14
            if digit_string[-1] not in ["1", "2" ,"3" ,"4"] or len(digit_string) >= 2 and digit_string[-2] == "1":
                ending = ""
            # [234] или X...X[234], но не 12, 13, 14
            else:
                ending = "ы"
        elif word_case == WordCase.DATIVE:
            ending = "ам"
        elif word_case == WordCase.INSTRUMENTAL:
            ending = "ами"
        else:  # WordCase.PREPOSITIONAL
            ending = "ах"

    return ending
