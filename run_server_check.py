from app.main import app

routes = sorted({route.path for route in app.routes})
print('app_loaded')
for route in routes:
    print(route)
