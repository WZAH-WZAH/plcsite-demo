from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.test import APIClient

from .models import Board, Post


class PostCreateSerializerExtrasTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.user = get_user_model().objects.create_user(username='u1', password='pw')
		Board.objects.filter(slug='test-games').delete()
		self.board = Board.objects.create(slug='test-games', title='游戏', description='', sort_order=0, is_active=True)

	def test_create_post_with_remove_cover_image_does_not_error(self):
		self.client.force_authenticate(user=self.user)

		payload = {
			'board': self.board.id,
			'title': 't1',
			'body': 'hello',
			'remove_cover_image': True,
		}
		resp = self.client.post('/api/posts/', payload, format='json')

		self.assertEqual(resp.status_code, 201, resp.content)
		post_id = resp.data.get('id')
		self.assertTrue(post_id)

		post = Post.objects.get(id=post_id)
		self.assertFalse(bool(post.cover_image))
		self.assertIn(getattr(post.cover_image, 'name', None), (None, ''))
