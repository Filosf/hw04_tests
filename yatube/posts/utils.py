from django.core.paginator import Paginator


POSTS_NUMBER = 10


def paginator_self(request, post):
    paginator = Paginator(post, POSTS_NUMBER)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
