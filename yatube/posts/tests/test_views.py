from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache

from ..forms import PostForm
from ..models import Group, Post, Follow

User = get_user_model()

INDEX_URL = 'posts:index'
GROUP_UPL = 'posts:group'
PROFILE_URL = 'posts:profile'
DETAIL_URL = 'posts:post_detail'
EDIT_URL = 'posts:post_edit'
CREATE_URL = 'posts:post_create'
FOLLOW_INDEX_URL = 'posts:follow_index'
FOLLOW_URL = 'posts:profile_follow'
UNFOLLOW_URL = 'posts:profile_unfollow'
PAGE_NOMBER = 3


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
        cache.clear()
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
                DETAIL_URL, kwargs={'post_id': self.post.id}
            ): 'posts/post_detail.html',
            reverse(
                EDIT_URL, kwargs={'post_id': self.post.id}
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
            one_object.image: self.post.image
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
            reverse(DETAIL_URL, kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.context.get('post').id, self.post.id)

    def test_post_edit_corrct(self):
        """Проверка post_edit.html"""
        response = self.authorized_client.get(reverse(
            EDIT_URL, kwargs={'post_id': self.post.id}
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

    def test_cache(self):
        """Тестируем КЕШ"""
        response1 = self.authorized_client.get(reverse(INDEX_URL))
        content1 = response1.content
        post_count = Post.objects.count()
        Post.objects.create(text='Тестовый текст', author=self.user)
        response2 = self.authorized_client.get(reverse(INDEX_URL))
        content2 = response2.content
        self.assertEqual(content1, content2)
        cache.clear()
        post_count1 = Post.objects.count()
        response3 = self.authorized_client.get(reverse(INDEX_URL))
        content3 = response3.content
        self.assertNotEqual(content1, content3)
        self.assertNotEqual(post_count, post_count1)


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username='author')
        cls.follower = User.objects.create(username='follower')

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.client_follower = Client()
        self.client_follower.force_login(self.follower)

    def test_follow(self):
        """Тестируем подписку авторизированного пользователя"""
        response = self.client_follower.post(
            reverse(FOLLOW_URL, kwargs={'username': self.author})
        )
        self.assertRedirects(
            response,
            reverse(PROFILE_URL, kwargs={'username': self.author})
        )
        follow = Follow.objects.all().latest('id')
        self.assertEqual(Follow.objects.count(), 1)
        self.assertEqual(follow.author.id, self.author.id)
        self.assertEqual(follow.user.id, self.follower.id)
        self.client_follower.post(
            reverse(FOLLOW_URL, kwargs={'username': self.author})
        )
        self.assertEqual(Follow.objects.count(), 1)

    def test_guest_follow(self):
        """Тестируем подписку не авторизированного пользователя"""
        follow_count = Follow.objects.count()
        self.guest_client.post(
            reverse(FOLLOW_URL, kwargs={'username': self.author})
        )
        self.assertEqual(Follow.objects.count(), follow_count)

    def test_unfollow(self):
        """Тестрируем отписку"""
        Follow.objects.create(user=self.follower, author=self.author)
        follow_count = Follow.objects.count()
        response = self.client_follower.post(
            reverse(UNFOLLOW_URL, kwargs={'username': self.author})
        )
        self.assertRedirects(
            response, reverse(PROFILE_URL, kwargs={'username': self.author})
        )
        self.assertEqual(Follow.objects.count(), follow_count - 1)

    def test_page_follow(self):
        """Тестрируем записи подписанного клиента"""
        post = Post.objects.create(author=self.author, text='TEXT')
        Follow.objects.create(user=self.follower, author=self.author)
        response = self.client_follower.get(reverse(FOLLOW_INDEX_URL))
        self.assertIn(post, response.context['page_obj'].object_list)

    def test_page_follow(self):
        """Тестрируем записи не подписанного клиента"""
        post = Post.objects.create(author=self.author, text='TEXT')
        response = self.client_follower.get(reverse(FOLLOW_INDEX_URL))
        self.assertNotIn(post, response.context['page_obj'].object_list)


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
        Post.objects.bulk_create(
            [
                Post(
                    text=f'Тестовый текст {i}',
                    author=cls.user,
                    group=cls.group
                )for i in range(settings.POSTS_NUMBER + PAGE_NOMBER)
            ]
        )

    def setUp(self):
        cache.clear()
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
                    reverse_name).context.get('page_obj')),
                    settings.POSTS_NUMBER)
                self.assertEqual(len(self.authorized_client.get(
                    reverse_name + '?page=2').context.get('page_obj')),
                    PAGE_NOMBER
                )
