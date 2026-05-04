from app.main import app
print('ml_routes_ok')
for route in sorted({route.path for route in app.routes if route.path.startswith('/api/quant/models') or route.path.startswith('/api/quant/scores') or route.path == '/quant'}):
    print(route)
