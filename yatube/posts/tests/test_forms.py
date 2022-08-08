import shutil
import tempfile

from http import HTTPStatus

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from ..models import Post, Group, User, Comment
from .. forms import CommentForm

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title="Заголовок",
            slug="the_group",
            description="Описание"
        )
        cls.post = Post.objects.create(
            text="Текст",
            pub_date='Дата',
            author=User.objects.create_user(username='test_name_2'),
            group=cls.group,
        )
        cls.comment = Comment.objects.create(
            text="Текст",
            created='Тестовая дата',
            author=cls.user,
            post=cls.post,
        )
        cls.urls = [
            '/profile/test_name_1/',
            '/group/the_group/',
            '/',
            '/posts/1/',
        ]

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент
        self.user1 = User.objects.create_user(username='test_name_1')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user1)
        # Создаем автора
        self.user2 = User.objects.get(username='test_name_2')
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.user2)

    def test_form_create_post(self):
        """Форма create действительно создает новый пост и перенаправляет."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Текст',
            'group': self.group.pk,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': 'test_name_1'}
        ))
        self.assertNotEqual(Post.objects.count(), posts_count)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_form_edit_post(self):
        """Форма edit правит пост и перенаправляет."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Текст',
            'group': self.group.pk
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': '1'}),
            data=form_data,
            follow=True,
            instance=Post.objects.get()
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': '1'}
        ))
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(
            Post.objects.filter(
                group=self.group.id,
                text=self.post.text,
            ).exists()
        )

    def test_comment_appears_in_post(self):
        """Проверка добавления комментария авторизованным пользователем."""
        form = CommentForm(data={
            'text': 'some comment',
        })
        self.assertTrue(form.is_valid())
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=[self.post.pk]),
            data=form.data,
            follow=True
        )
        # Проверяем наличие комментариев
        self.assertEqual(self.post.comments.last().text, form.data['text'])
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            args=[self.post.pk])
        )

    def test_comment_not_appears_in_post(self):
        """Проверка добавления комментария неавторизованным пользователем."""
        form = CommentForm(data={
            'text': 'Текст',
        })
        self.assertTrue(form.is_valid())
        # Отправляем POST-запрос
        response = self.guest_client.post(
            reverse('posts:add_comment', args=[self.post.pk]),
            data=form.data,
            follow=True
        )
        # Проверяем, сработал ли редирект на логин
        self.assertRedirects(response, reverse(
            'users:login') + '?next=/posts/1/comment/'
        )

    def test_create_image_post(self):
        """Проверка загрузки картинок во все необходимые страницы."""
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
            'text': 'Текст',
            'group': self.group.pk,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект создания поста
        self.assertRedirects(response, '/profile/test_name_1/')
        # Проверяем, сработал ли редирект редактирования поста
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                group=self.group.id,
                text=form_data['text'],
                image=f'posts/{uploaded.name}',
            ).exists()
        )
        # Проверка контекста
        response_1 = Post.objects.all().first()
        response_test_1 = response_1.text
        response_test_2 = response_1.group.id
        response_test_3 = response_1.image
        self.assertEqual(response_test_1, form_data['text'])
        self.assertEqual(response_test_2, form_data['group'])
        self.assertEqual(response_test_3, f'posts/{uploaded.name}')

    def test_edit_image_post(self):
        """Проверка страницы редактирования вместе с картинками."""
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
            'text': 'Текст',
            'group': self.group.pk,
            'image': uploaded,
        }

        response = self.authorized_client_author.post(
            reverse('posts:post_edit', kwargs={'post_id': '1'}),
            data=form_data,
            follow=True,
            instance=Post.objects.get()
        )

        # Проверяем, сработал ли редирект редактирования поста
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': '1'}))
        # Количество постов не увеличено
        self.assertEqual(Post.objects.count(), posts_count)
