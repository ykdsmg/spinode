from app.db.manager import DBManager

async def load_mercado_shop():
    from app.platform.MercadoShop import MercadoShop

    shops = await DBManager.select(
        "SELECT A.app_id, A.secret, A.user_id, A.seller_id, A.shop_name, A.shop_names, A.business_unit, A.timezone, B.access_token, B.refresh_token, B.GetTime as get_time \
        FROM mercado_app_seller A LEFT JOIN mercado_token B ON A.seller_id = B.user_id and B.state = 1")

    return {shop['seller_id']: MercadoShop(**shop) for shop in shops}


async def load_falabella_shop():
    from app.platform.FalabellaShop import FalabellaShop

    shops = await DBManager.select("SELECT SellerID as seller_id,UserID as user_id,ApiKey as api_key,BusinessUnit as business_unit,ShopName as shop_name,ShopNameS as shop_names,TimeZone as timezone FROM falabella_config")

    return {shop['seller_id']: FalabellaShop(**shop) for shop in shops}


async def load_paris_shop():
    from app.platform.ParisShop import ParisShop

    shops = await DBManager.select("SELECT seller_id,api_key FROM shop_config_paris")

    return {shop['seller_id']: ParisShop(seller_id=shop['seller_id'], api_key=shop['api_key']) for shop in shops}
