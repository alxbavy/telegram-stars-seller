import re
from typing import final, override, cast

from django import forms
from django.core.exceptions import ValidationError

from core.models import Broadcast


@final
class BroadcastForm(forms.ModelForm):
    @final
    class Meta:
        model = Broadcast
        fields = '__all__'

    @override
    def clean(self):
        cleaned_data = super().clean()
        text = cast(str, cleaned_data.get("text", ""))
        media = cleaned_data.get("media")
        btn_texts = cleaned_data.get("button_texts")
        btn_urls = cleaned_data.get("button_urls")

        clean_text_length = len(re.sub(r'<[^>]+>', '', text))
        if media and clean_text_length > 1024:
            raise ValidationError({
                "text": f"С прикрепленным медиа текст не должен превышать 1024 символа (сейчас {clean_text_length})."
            })
        elif not media and clean_text_length > 4096:
            raise ValidationError({
                "text": f"Текст не должен превышать 4096 символов (сейчас {clean_text_length})."
            })

        if bool(btn_texts) != bool(btn_urls):
            if not btn_texts:
                raise ValidationError({
                    "button_texts": "Это поле должно быть заполнено, так как заполнено поле с URL."
                })
            raise ValidationError({
                "button_urls": "Это поле должно быть заполнено, так как заполнено поле с текстами."
            })

        if not isinstance(btn_texts, list) and btn_texts is not None:
            raise ValidationError({
                "button_texts": "Поле для текста кнопок должно быть списками списков (например: [[\"Кнопка\"]])."
            })

        if not isinstance(btn_urls, list) and btn_urls is not None:
            raise ValidationError({
                "button_urls": "Поле для url кнопок должно быть списками списков (например: [[\"my_url.ru\"]])."
            })

        btn_texts = cast(list[object] | None, btn_texts)  # noqa
        btn_urls = cast(list[object] | None, btn_urls)  # noqa

        if btn_texts and btn_urls:
            btn_texts_len = len(btn_texts)
            btn_urls_len = len(btn_urls)
            if btn_texts_len < btn_urls_len:
                raise ValidationError({
                    "button_texts": f"Не хватает {btn_urls_len - btn_texts_len} строк, так как в URL их {btn_urls_len}."
                })
            if btn_urls_len < btn_texts_len:
                raise ValidationError({
                    "button_urls": f"Не хватает {btn_texts_len - btn_urls_len} строк, так как в текстах их {btn_texts_len}."
                })

            for i, (text_row, url_row) in enumerate(zip(btn_texts, btn_urls)):
                if not isinstance(text_row, list):
                    raise ValidationError({"button_texts": f"Строка {i + 1} должна быть списком."})
                if not isinstance(url_row, list):
                    raise ValidationError({"button_urls": f"Строка {i + 1} должна быть списком."})

                text_row = cast(list[list[object]], text_row)  # noqa
                text_row_len = len(text_row)
                url_row = cast(list[list[object]], url_row)  # noqa
                url_row_len = len(url_row)

                if text_row_len < url_row_len:
                    err_msg = (
                        f"В строке {i + 1} не хватает {url_row_len - text_row_len} текстов, "
                        f"так как в URL их {url_row_len}."
                    )
                    raise ValidationError({"button_texts": err_msg})
                if url_row_len < text_row_len:
                    err_msg = (
                        f"В строке {i + 1} не хватает {text_row_len - url_row_len} URL, "
                        f"так как в текстах их {text_row_len}."
                    )
                    raise ValidationError({"button_urls": err_msg})

                for j, text in enumerate(text_row):
                    if not isinstance(text, str):
                        raise ValidationError({
                            "button_texts": f"В строке {i + 1} текст №{j + 1} должен быть в двойных кавычках."
                        })

                for j, url in enumerate(url_row):
                    if not isinstance(url, str):
                        raise ValidationError({
                            "button_urls": f"В строке {i + 1} URL №{j + 1} должен быть в двойных кавычках."
                        })

        return cleaned_data
