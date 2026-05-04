from app.main import app

for route in sorted({route.path for route in app.routes if 'quant' in route.path or route.path == '/quant'}):
    print(route)
