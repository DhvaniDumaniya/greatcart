from .models import Category


# return dictionary and take argument as request
def menu_links(request):
    links = Category.objects.all()
    return dict(links=links)