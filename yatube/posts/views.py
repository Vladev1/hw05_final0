from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.core.paginator import Paginator
from django.views.decorators.cache import cache_page

from .models import Post, Group, User, Follow, Like
from .forms import PostForm, CommentForm

QT_POST_PG = 10


def paginator(request, queryset):
    pagenator = Paginator(queryset, QT_POST_PG)
    page_number = request.GET.get('page')
    page_obj = pagenator.get_page(page_number)
    return page_obj


@cache_page(1)
def index(request):
    post_list = Post.objects.all()
    context = {
        'page_obj': paginator(request, post_list),
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    context = {
        'group': group,
        'page_obj': paginator(request, posts),
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    post = author.posts.all()
    following = (
        request.user.is_authenticated
        and author.following.filter(user=request.user).exists()
    )
    liking = (
        request.user.is_authenticated
        and author.liking.filter(user=request.user).exists()
    )
    context = {
        'author': author,
        'page_obj': paginator(request, post),
        'following': following,
        'liking': liking,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm()
    comments = post.comments.all()
    context = {
        'post': post,
        'form': form,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    username = request.user.username
    if not form.is_valid():
        return render(request, 'posts/create_post.html', {'form': form})
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect('posts:profile', username=username)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:post_detail', post_id=post_id)
    context = {'form': form, 'post': post, 'is_edit': True}
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    # информация о текущем пользователе доступна в переменной request.user
    post = Post.objects.filter(author__following__user=request.user).all()
    context = {
        'page_obj': paginator(request, post),
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    # Подписаться на автора
    if request.user.username == username:
        return redirect("posts:profile", username=username)
    following = get_object_or_404(User, username=username)
    already_follows = Follow.objects.get_or_create(
        user=request.user,
        author=following
    )
    if not already_follows:
        Follow.objects.create(user=request.user, author=following)
    return redirect("posts:profile", username=username)


@login_required
def profile_unfollow(request, username):
    # Дизлайк, отписка
    following = get_object_or_404(User, username=username)
    follower = get_object_or_404(Follow, author=following, user=request.user)
    follower.delete()
    return redirect("posts:profile", username=username)


@login_required
def liked_index(request):
    # информация о текущем пользователе доступна в переменной request.user
    post = Post.objects.all()
    like = Post.objects.filter(like__liking__author=request.user).all()
    context = {
        'page_obj': paginator(request, post),
        'like': like
    }
    return render(request, 'posts/like.html', context)


@login_required
def post_liked(request, username, post_id):
    # Подписаться на автора
    like = get_object_or_404(Post, pk=post_id)
    liking = get_object_or_404(User, username=username)
    already_like = Like.objects.get_or_create(
        user=request.user,
        post=like,
        username=liking,
    )
    if not already_like:
        Like.objects.create(user=request.user, post=like, username=liking,)
    return redirect("posts:index", pk=post_id)


@login_required
def post_unliked(request, post_id):
    # Дизлайк, отписка
    like = get_object_or_404(Post, pk=post_id)
    liker = get_object_or_404(Like, post=like, user=request.user)
    liker.delete()
    return redirect("posts:index", pk=post_id)
