from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache

from ..models import Group, Post

User = get_user_model()

INDEX_URL = 'posts:index'
GROUP_UPL = 'posts:group'
PROFILE_URL = 'posts:profile'
EDIT_URL = 'posts:post_edit'
CREATE_URL = 'posts:post_create'
DETAIL_URL = 'posts:post_detail'
FOLLOW_INDEX_URL = 'posts:follow_index'


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовое название',
            description='Тестовый текст',
            slug='test-slug'
        )
        cls.user = User.objects.create_user(
            username='HasNoNeme'
        )
        cls.not_user = User.objects.create_user(
            username='No user'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=User.objects.create_user(
                username='test author'
            )
        )
        cls.templates_url_names_public = {
            'posts/index.html': reverse(INDEX_URL),
            'posts/group_list.html': reverse(
                GROUP_UPL,
                kwargs={'slug': cls.group.slug},
            ),
            'posts/profile.html': reverse(
                PROFILE_URL,
                kwargs={'username': cls.user.username},
            ),
            'posts/post_detail.html': reverse(
                DETAIL_URL,
                kwargs={'post_id': cls.post.id}
            )
        }
        cls.templates_url_names_prevate = {
            'posts/post_create.html': reverse(CREATE_URL),
            'posts/follow.html': reverse(FOLLOW_INDEX_URL)
        }
        cls.templates_url_names = {
            'posts/index.html': reverse(INDEX_URL),
            'posts/group_list.html': reverse(
                GROUP_UPL,
                kwargs={'slug': cls.group.slug},
            ),
            'posts/profile.html': reverse(
                PROFILE_URL,
                kwargs={'username': cls.user.username},
            ),
            'posts/post_create.html': reverse(CREATE_URL),
        }

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.not_author_user = Client()
        self.not_author_user.force_login(self.not_user)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for template, reverse_name in self.templates_url_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_urls_guest_public(self):
        """Проверка неавторизированого пользователья, публичных страниц."""
        for template, reverse_name in self.templates_url_names_public.items():
            with self.subTest(template=template):
                response = self.guest_client.get(reverse_name)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_guest_private(self):
        """Проверка неавторизированого пользователья, приватных страниц."""
        for template, reverse_name in self.templates_url_names_prevate.items():
            with self.subTest(template=template):
                response = self.guest_client.get(reverse_name)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)
        response = self.guest_client.get(
            reverse(
                EDIT_URL,
                kwargs={'post_id': self.post.id},
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_create_post_authorized(self):
        """Проверка авторизованного пользователя."""
        for template, reverse_name in self.templates_url_names.items():
            with self.subTest(template=template):
                if reverse_name == reverse(
                    EDIT_URL,
                    kwargs={'post_id': self.post.id},
                ):
                    response = self.not_author_user.get(reverse_name)
                    self.assertEqual(response.status_code, HTTPStatus.FOUND)
                else:
                    response = self.not_author_user.get(reverse_name)
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_page_is_available_only_to_the_author(self):
        """Проверка на автора."""
        for template, reverse_name in self.templates_url_names.items():
            with self.subTest(template=template):
                reverse = self.authorized_client.get(reverse_name)
                self.assertEqual(reverse.status_code, HTTPStatus.OK)

    def test_unexisting_page(self):
        """Проверка на существование страницы"""
        reverse = self.guest_client.get('/page_404/')
        self.assertEqual(reverse.status_code, HTTPStatus.NOT_FOUND)
