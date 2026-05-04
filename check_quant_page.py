from app.main import app
print('routes_ok')
for route in sorted({route.path for route in app.routes if route.path.startswith('/api/quant') or route.path == '/quant'}):
    print(route)
