from core.models import PromoCode


class PromoCodeRepository:
    model: type[PromoCode] = PromoCode

    async def get_promo_by_id(
            self,
            db_id: int,
            is_prefetch_related: bool = False,
            is_use_is_active: bool = True, is_active: bool = True
    ) -> PromoCode | None:
        query = self.model.objects.filter(db_id=db_id)

        if is_use_is_active:
            query = query.filter(is_active=is_active)

        if is_prefetch_related:
            query = query.prefetch_related("telegram_users")

        return await query.afirst()

    async def get_promo_by_name(
            self,
            name: str,
            is_prefetch_related: bool = False,
            is_use_is_active: bool = True, is_active: bool = True
    ) -> PromoCode | None:
        query = self.model.objects.filter(name=name)

        if is_use_is_active:
            query = query.filter(is_active=is_active)

        if is_prefetch_related:
            query = query.prefetch_related("telegram_users")

        return await query.afirst()
