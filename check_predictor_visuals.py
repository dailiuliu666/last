from app.main import app
print('predictor_visuals_ok')
for route in sorted({route.path for route in app.routes if route.path.startswith('/api/predictor') or route.path == '/predictor'}):
    print(route)
