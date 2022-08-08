from django.test import TestCase

from ..models import Post, Group, User


class PostsModelTest(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title="Заголовок тестовой задачи",
            slug="test-slug",
            description="Описание тестовой группы"
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text="Описание тестового поста"
        )

    def test_models_name_group_have_correct_object_names(self):
        """" Просмотр тестов имени группы."""
        group = PostsModelTest.group
        field_verboses = {
            'title': 'Заголовочек',
            'slug': 'Слаг адрес',
            'description': 'Описание группы',
        }
        for field, expected_value in field_verboses.items():
            with self.subTest(field=field):
                response = group._meta.get_field(field).verbose_name
                self.assertEqual(response, expected_value)

    def test_models_post_have_correct_object_names(self):
        """" Просмотр тестов имени поста."""
        post = PostsModelTest.post
        field_verboses = {
            'text': 'Мысли великих'
        }
        for field, expected in field_verboses.items():
            with self.subTest(field=field):
                response = post._meta.get_field(field).verbose_name
                self.assertEqual(response, expected)

    def test_models_have_correct_object_names(self):
        """" Просмотр количества символов поста."""
        post = PostsModelTest.post
        self.assertEqual(post.text[:15], str(post))
