import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../auth/providers.dart';

final postsProvider = FutureProvider.autoDispose<List<dynamic>>((ref) async {
  final json = await ref.watch(apiClientProvider).get('/posts');
  return (json as Map<String, dynamic>)['items'] as List<dynamic>;
});

class CommunityScreen extends ConsumerWidget {
  const CommunityScreen({super.key});

  Future<void> _compose(BuildContext context, WidgetRef ref) async {
    final controller = TextEditingController();
    final selected = <XFile>[];
    final content = await showDialog<String>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(builder: (context, setState) => AlertDialog(
        title: const Text('새 게시글'),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(
            controller: controller,
            autofocus: true,
            minLines: 4,
            maxLines: 8,
            decoration: const InputDecoration(hintText: '드라이브 이야기를 나눠보세요.'),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: () async {
              final files = await ImagePicker().pickMultiImage(imageQuality: 85, limit: 5);
              setState(() {
                selected
                  ..clear()
                  ..addAll(files.take(5));
              });
            },
            icon: const Icon(Icons.photo_library_outlined),
            label: Text('사진 ${selected.length}/5'),
          ),
          if (selected.isNotEmpty)
            SizedBox(
              height: 72,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: selected.length,
                separatorBuilder: (_, _) => const SizedBox(width: 8),
                itemBuilder: (_, index) => Image.file(
                  File(selected[index].path), width: 72, height: 72, fit: BoxFit.cover,
                ),
              ),
            ),
        ])),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('취소')),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, controller.text.trim()),
            child: const Text('등록'),
          ),
        ],
      )),
    );
    if (content == null || content.isEmpty || !context.mounted) {
      controller.dispose();
      return;
    }
    try {
      final urls = <String>[];
      for (final file in selected) {
        urls.add(await ref.read(apiClientProvider).uploadImage(File(file.path)));
      }
      await ref.read(apiClientProvider).post('/posts', body: {
        'content': content,
        'image_urls': urls,
      });
      ref.invalidate(postsProvider);
    } catch (error) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
    } finally {
      controller.dispose();
    }
  }

  Future<void> _comments(BuildContext context, WidgetRef ref, int postId) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => _CommentSheet(postId: postId),
    );
    ref.invalidate(postsProvider);
  }

  Future<void> _postAction(
    BuildContext context,
    WidgetRef ref,
    Map<String, dynamic> post,
    String action,
  ) async {
    if (action == 'delete') {
      await ref.read(apiClientProvider).delete('/posts/${post['id']}');
    } else if (action == 'report') {
      await ref.read(apiClientProvider).post('/reports', body: {
        'target_type': 'post',
        'target_id': post['id'],
        'reason': 'inappropriate_content',
        'details': '앱에서 사용자가 신고한 게시글',
      });
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('신고가 접수되었습니다.')));
      }
    } else if (action == 'block') {
      await ref.read(apiClientProvider).put('/me/blocks', body: {'user_id': post['author_id']});
    }
    ref.invalidate(postsProvider);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final posts = ref.watch(postsProvider);
    final myId = int.tryParse(ref.watch(authControllerProvider).session?.userId ?? '');
    return Scaffold(
      appBar: AppBar(title: const Text('커뮤니티')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _compose(context, ref),
        icon: const Icon(Icons.edit),
        label: const Text('글쓰기'),
      ),
      body: posts.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(child: Text('게시글을 불러오지 못했습니다. $error')),
        data: (items) => RefreshIndicator(
          onRefresh: () => ref.refresh(postsProvider.future),
          child: ListView.builder(
            itemCount: items.isEmpty ? 1 : items.length,
            itemBuilder: (context, index) {
              if (items.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(child: Text('아직 게시글이 없습니다.')),
                );
              }
              final post = items[index] as Map<String, dynamic>;
              final images = (post['image_urls'] as List<dynamic>? ?? []).cast<String>();
              return Card(
                margin: const EdgeInsets.fromLTRB(12, 8, 12, 0),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  ListTile(
                    title: Text(post['author_nickname']?.toString() ?? '사용자'),
                    trailing: PopupMenuButton<String>(
                      onSelected: (value) => _postAction(context, ref, post, value),
                      itemBuilder: (_) => post['author_id'] == myId
                          ? const [PopupMenuItem(value: 'delete', child: Text('삭제'))]
                          : const [
                              PopupMenuItem(value: 'report', child: Text('신고')),
                              PopupMenuItem(value: 'block', child: Text('사용자 차단')),
                            ],
                    ),
                  ),
                  if (images.isNotEmpty)
                    SizedBox(
                      height: 240,
                      child: PageView(
                        children: images.map((url) => Image.network(url, fit: BoxFit.cover)).toList(),
                      ),
                    ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                    child: Text(post['content'].toString()),
                  ),
                  Row(children: [
                    IconButton(
                      icon: Icon(post['liked_by_me'] == true ? Icons.favorite : Icons.favorite_border),
                      onPressed: () async {
                        final api = ref.read(apiClientProvider);
                        if (post['liked_by_me'] == true) {
                          await api.delete('/posts/${post['id']}/like');
                        } else {
                          await api.put('/posts/${post['id']}/like');
                        }
                        ref.invalidate(postsProvider);
                      },
                    ),
                    Text('${post['like_count']}'),
                    const SizedBox(width: 12),
                    TextButton.icon(
                      onPressed: () => _comments(context, ref, post['id'] as int),
                      icon: const Icon(Icons.chat_bubble_outline),
                      label: Text('${post['comment_count']} 댓글'),
                    ),
                  ]),
                ]),
              );
            },
          ),
        ),
      ),
    );
  }
}

class _CommentSheet extends ConsumerStatefulWidget {
  const _CommentSheet({required this.postId});

  final int postId;

  @override
  ConsumerState<_CommentSheet> createState() => _CommentSheetState();
}

class _CommentSheetState extends ConsumerState<_CommentSheet> {
  final _controller = TextEditingController();
  List<Map<String, dynamic>> _comments = [];
  bool _loading = true;
  bool _submitting = false;
  String? _error;

  int get _myUserId =>
      int.parse(ref.read(authControllerProvider).session!.userId);

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final raw = await ref
          .read(apiClientProvider)
          .getAs<List<dynamic>>('/posts/${widget.postId}/comments');
      if (!mounted) return;
      setState(() {
        _comments = raw.cast<Map<String, dynamic>>();
        _loading = false;
        _error = null;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = '$error';
      });
    }
  }

  Future<void> _submit() async {
    final content = _controller.text.trim();
    if (content.isEmpty || _submitting) return;
    setState(() => _submitting = true);
    try {
      await ref.read(apiClientProvider).post(
        '/posts/${widget.postId}/comments',
        body: {'content': content},
      );
      _controller.clear();
      await _load();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('댓글을 등록하지 못했습니다. $error')),
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _delete(int commentId) async {
    try {
      await ref.read(apiClientProvider).delete('/comments/$commentId');
      await _load();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('댓글을 삭제하지 못했습니다. $error')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) => SafeArea(
    child: Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.viewInsetsOf(context).bottom,
      ),
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * .72,
        child: Column(
          children: [
            const Padding(
              padding: EdgeInsets.all(12),
              child: Text('댓글', style: TextStyle(fontSize: 18)),
            ),
            Expanded(child: _commentList()),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      enabled: !_submitting,
                      decoration: const InputDecoration(hintText: '댓글 입력'),
                      onSubmitted: (_) => _submit(),
                    ),
                  ),
                  IconButton(
                    onPressed: _submitting ? null : _submit,
                    icon: _submitting
                        ? const SizedBox.square(
                            dimension: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    ),
  );

  Widget _commentList() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error!),
            TextButton(onPressed: _load, child: const Text('다시 시도')),
          ],
        ),
      );
    }
    if (_comments.isEmpty) {
      return const Center(child: Text('첫 댓글을 남겨보세요.'));
    }
    return ListView.builder(
      itemCount: _comments.length,
      itemBuilder: (_, index) {
        final comment = _comments[index];
        return ListTile(
          title: Text(comment['author_nickname']?.toString() ?? '사용자'),
          subtitle: Text(comment['content'].toString()),
          trailing: comment['author_id'] == _myUserId
              ? IconButton(
                  icon: const Icon(Icons.delete_outline),
                  onPressed: () => _delete(comment['id'] as int),
                )
              : null,
        );
      },
    );
  }
}
