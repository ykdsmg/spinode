def load_mercado_shop():
    pass


def load_falabella_shop():
    pass


def load_paris_shop():
    from app.platform.ParisShop import ParisShop
    return {
        "0001": ParisShop(
            seller_id="",
            user_id="",
            api_key="18b86518-a2ff-4900-b048-7e404a688885",
            country="",
            shop_name="",
            shop_code="Paris-ED",
            time_zone="",
        ),
        "0002": ParisShop(
            seller_id="",
            user_id="",
            api_key="36e2180a-9cf2-47d8-b7ea-11c1aa0e35ec",
            country="",
            shop_name="",
            shop_code="Paris-HD",
            time_zone="",
        ),
        "0003": ParisShop(
            seller_id="",
            user_id="",
            api_key="36f1ee21-da89-43ed-b21b-eed0227e04fa",
            country="",
            shop_name="",
            shop_code="Paris-HD",
            time_zone="",
        )
    }
