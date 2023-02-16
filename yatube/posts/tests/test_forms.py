from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()

PROFILE_URL = 'posts:profile'
DETAIL_URL = 'posts:post_detail'
EDIT_URL = 'posts:post_edit'
CREATE_URL = 'posts:post_create'


class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="HasNoName")
        cls.group = Group.objects.create(
            title='Тестовое название',
            description='Тестовый текст поста',
            slug='test-slug'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст поста',
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_create_authorized_user(self):
        """Запись создает авторизированный пользователь."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст поста',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse(CREATE_URL),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                PROFILE_URL,
                kwargs={'username': self.user.username}
            )
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(Post.objects.filter(
            text='Тестовый текст поста').exists())

    def test_post_edit_authorized_user(self):
        """Запись редактирует авторизованый пользователь."""
        post = Post.objects.create(
            text='Текст для редактирования',
            author=self.user,
            group=self.group,
        )
        form_data = {
            'text': 'Отредактированный текст',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse(CREATE_URL),
            data=form_data,
            follow=True,
        )
        response = self.authorized_client.post(
            reverse(EDIT_URL, args=[self.post.id]), data=form_data, follow=True
        )
        self.assertRedirects(
            response,
            reverse(DETAIL_URL, kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        post = Post.objects.get(id=self.post.id)
        self.assertTrue(post.text == form_data['text'])
        self.assertTrue(post.author == self.user)
        self.assertTrue(post.group_id == form_data['group'])

    def test_post_create_not_authorized_user(self):
        """Запись создает не авторизированный пользователь."""
        posts_count = Post.objects.count()
        form_data = {
            'text': '',
            'group': self.group.id,
        }
        response = self.guest_client.post(
            reverse(CREATE_URL),
            data=form_data,
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        redirect = reverse('login') + '?next=' + reverse(CREATE_URL)
        self.assertRedirects(response, redirect)
        self.assertEqual(Post.objects.count(), posts_count)
