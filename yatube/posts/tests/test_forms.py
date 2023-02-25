import tempfile
import shutil
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from ..models import Group, Post, Comment

User = get_user_model()

PROFILE_URL = 'posts:profile'
DETAIL_URL = 'posts:post_detail'
EDIT_URL = 'posts:post_edit'
CREATE_URL = 'posts:post_create'
COMMENT_URL = 'posts:add_comment'
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="HasNoName")
        cls.group = Group.objects.create(
            title='Тестовое название',
            description='Тестовый описание',
            slug='test_slug'
        )
        cls.new_group = Group.objects.create(
            title='Второе тестовое название',
            description='Второе тестовый описание',
            slug='testslug'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст поста',
            author=cls.user,
            group=cls.group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_create_authorized_user(self):
        """Запись создает авторизированный пользователь."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': self.post.text,
            'group': self.group.id,
            'image': uploaded,
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
        new_post = Post.objects.latest('id')
        self.assertEqual(new_post.author, self.user)
        self.assertEqual(new_post.group, self.group)
        self.assertEqual(new_post.image.name, 'posts/small.gif')

    def test_post_edit_authorized_user(self):
        """Запись редактирует авторизованый пользователь."""
        post = self.post
        form_data = {
            'text': 'Отредактированный текст',
            'group': self.new_group.id,
        }
        response = self.authorized_client.post(
            reverse(EDIT_URL, args=[self.post.id]), data=form_data, follow=True
        )
        self.assertRedirects(
            response,
            reverse(DETAIL_URL, kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        post = Post.objects.get(id=self.post.id)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group_id, form_data['group'])
        old_group_response = self.authorized_client.get(
            reverse('posts:group', args=(self.group.slug,))
        )
        self.assertEqual(
            old_group_response.context['page_obj'].paginator.count,
            0
        )
        new_group_response = self.authorized_client.get(
            reverse('posts:group', args=(self.new_group.slug,))
        )
        self.assertEqual(
            new_group_response.context['page_obj'].paginator.count,
            1
        )

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

    def test_comment(self):
        """Проверка комментариев"""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Текст комментария',
        }
        response = self.authorized_client.post(
            reverse(COMMENT_URL, kwargs={'post_id': self.post.id}),
            data=form_data,
        )
        self.assertRedirects(
            response,
            reverse(DETAIL_URL, kwargs={'post_id': self.post.id})
        )
        self.assertTrue(Comment.objects.filter(
            text='Текст комментария').exists())
        self.assertEqual(
            Comment.objects.count(),
            comments_count + 1
        )
        response = self.guest_client.post(
            reverse(COMMENT_URL, kwargs={'post_id': self.post.id}),
            data=form_data,
        )
        self.assertEqual(
            Comment.objects.count(),
            comments_count + 1
        )
