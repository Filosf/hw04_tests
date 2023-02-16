from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from ..forms import PostForm
from ..models import Group, Post

User = get_user_model()

INDEX_URL = 'posts:index'
GROUP_UPL = 'posts:group'
PROFILE_URL = 'posts:profile'
DETAIL_URL = 'posts:post_detail'
EDIT_URL = 'posts:post_edit'
CREATE_URL = 'posts:post_create'


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="HasNoName")
        cls.group = Group.objects.create(
            title='Тестовое название',
            description='Тестовый текст',
            slug='test-slug'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_urls_users_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            reverse(INDEX_URL): 'posts/index.html',
            reverse(
                GROUP_UPL, kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse(
                PROFILE_URL, kwargs={'username': self.user}
            ): 'posts/profile.html',
            reverse(
                DETAIL_URL, kwargs={'post_id': self.post.pk}
            ): 'posts/post_detail.html',
            reverse(
                EDIT_URL, kwargs={'post_id': self.post.pk}
            ): 'posts/post_create.html',
            reverse(CREATE_URL): 'posts/post_create.html'
        }
        for reverse_name, template in templates_url_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def post_verification(self, one_object):
        """Проверка постов."""
        context = {
            one_object.text: self.post.text,
            one_object.author.username: self.post.author.username,
            one_object.group.title: self.group.title,
            one_object.id: self.post.id,
        }
        for key, value in context.items():
            with self.subTest(key=key):
                self.assertEqual(key, value)

    def test_index_correct(self):
        """Проверка index.html"""
        response = self.authorized_client.get(reverse(INDEX_URL))
        one_object = response.context['page_obj'][0]
        self.post_verification(one_object)

    def text_group_correct(self):
        """Проверка group_list.html"""
        response = self.authorized_client.get(
            reverse(GROUP_UPL, kwargs={'slug': self.group.slug})
        )
        context_group = {
            'title': self.group.title,
            'description': self.group.description,
            'slug': self.group.slug,
            'id': self.group.id,
        }
        for key, value in context_group.items():
            with self.subTest(key=key):
                self.assertEqual(
                    getattr(response.context.get('group'), key), value
                )

    def test_profile_correct(self):
        """Проверка profile.html"""
        response = self.authorized_client.get(
            reverse(PROFILE_URL, kwargs={'username': self.user})
        )
        one_object = response.context['page_obj'][0]
        self.post_verification(one_object)

    def test_post_detail_correct(self):
        """Проверка detail.html"""
        response = self.authorized_client.get(
            reverse(DETAIL_URL, kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(response.context.get('post').pk, self.post.pk)

    def test_post_edit_corrct(self):
        """post_edit.html"""
        response = self.authorized_client.get(reverse(
            EDIT_URL, kwargs={'post_id': self.post.pk}
        ))
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context.get('form'), PostForm)
        self.assertIs(type(response.context.get('is_edit')), bool)
        self.assertEqual(response.context.get('is_edit'), True)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_correct(self):
        """post_create.html"""
        response = self.authorized_client.get(reverse(CREATE_URL))
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context.get('form'), PostForm)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовое название',
            description='Тестовый текст',
            slug='test-slug'
        )
        cls.post = [
            Post.objects.create(
                text=f'Тестовый текст {i}',
                author=cls.user,
                group=cls.group
            )
            for i in range(13)
        ]

    def setUp(self):
        self.authorized_client = Client()

    def test_paginator(self):
        """Paginator"""
        url_page_paginator = (
            reverse(INDEX_URL),
            reverse(GROUP_UPL, kwargs={'slug': self.group.slug}),
            reverse(PROFILE_URL, kwargs={'username': self.user.username}),
        )
        for reverse_name in url_page_paginator:
            with self.subTest(reverse_name=reverse_name):
                self.assertEqual(len(self.authorized_client.get(
                    reverse_name).context.get('page_obj')), 10)
                self.assertEqual(len(self.authorized_client.get(
                    reverse_name + '?page=2').context.get('page_obj')), 3)
