import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../admin/presentation/admin_screen.dart';
import '../../auth/providers.dart';

final profileProvider = FutureProvider.autoDispose<Map<String, dynamic>>(
  (ref) async => await ref.watch(apiClientProvider).get('/me/profile') as Map<String, dynamic>,
);

final myDriveRecordsProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final page = await ref.watch(apiClientProvider).get('/me/drive-records') as Map<String, dynamic>;
  return (page['items'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
});

final myPostsProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final page = await ref.watch(apiClientProvider).get('/me/posts') as Map<String, dynamic>;
  return (page['items'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
});

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  Future<void> _editProfile(
    BuildContext context,
    WidgetRef ref,
    Map<String, dynamic> profile,
  ) async {
    final nickname = TextEditingController(text: profile['nickname']?.toString());
    final bio = TextEditingController(text: profile['bio']?.toString());
    String? imageUrl = profile['profile_image_url']?.toString();
    final body = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => StatefulBuilder(builder: (context, setState) => AlertDialog(
        title: const Text('프로필 수정'),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          CircleAvatar(
            radius: 40,
            backgroundImage: imageUrl == null ? null : NetworkImage(imageUrl!),
            child: imageUrl == null ? const Icon(Icons.person, size: 40) : null,
          ),
          TextButton.icon(
            onPressed: () async {
              final file = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 85);
              if (file == null) return;
              try {
                final url = await ref.read(apiClientProvider).uploadImage(File(file.path));
                setState(() => imageUrl = url);
              } catch (error) {
                if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
              }
            },
            icon: const Icon(Icons.photo_camera_outlined),
            label: const Text('사진 변경'),
          ),
          TextField(controller: nickname, decoration: const InputDecoration(labelText: '닉네임')),
          TextField(controller: bio, maxLines: 3, decoration: const InputDecoration(labelText: '소개')),
        ])),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('취소')),
          FilledButton(onPressed: () => Navigator.pop(context, {
            'nickname': nickname.text.trim(),
            'bio': bio.text.trim(),
            'profile_image_url': imageUrl,
          }), child: const Text('저장')),
        ],
      )),
    );
    nickname.dispose();
    bio.dispose();
    if (body == null) return;
    await ref.read(apiClientProvider).patch('/me/profile', body: body);
    ref.invalidate(profileProvider);
  }

  Future<void> _addVehicle(BuildContext context, WidgetRef ref) async {
    final manufacturer = TextEditingController();
    final model = TextEditingController();
    final year = TextEditingController();
    var primary = true;
    final body = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => StatefulBuilder(builder: (context, setState) => AlertDialog(
        title: const Text('차량 등록'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: manufacturer, decoration: const InputDecoration(labelText: '제조사')),
          TextField(controller: model, decoration: const InputDecoration(labelText: '차종')),
          TextField(controller: year, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: '연식')),
          SwitchListTile(value: primary, onChanged: (value) => setState(() => primary = value), title: const Text('대표 차량')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('취소')),
          FilledButton(onPressed: () => Navigator.pop(context, {
            'manufacturer': manufacturer.text.trim().isEmpty ? null : manufacturer.text.trim(),
            'model_name': model.text.trim(),
            'model_year': int.tryParse(year.text),
            'is_primary': primary,
          }), child: const Text('등록')),
        ],
      )),
    );
    for (final controller in [manufacturer, model, year]) {
      controller.dispose();
    }
    if (body == null || (body['model_name'] as String).isEmpty) return;
    await ref.read(apiClientProvider).post('/me/vehicles', body: body);
    ref.invalidate(profileProvider);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(profileProvider);
    final records = ref.watch(myDriveRecordsProvider);
    final posts = ref.watch(myPostsProvider);
    final isAdmin = ref.watch(authControllerProvider).session?.isAdmin == true;
    return Scaffold(
      appBar: AppBar(
        title: const Text('프로필'),
        actions: [
          IconButton(
            tooltip: '로그아웃',
            onPressed: () => ref.read(authControllerProvider.notifier).signOut(),
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: profile.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(child: Text('$error')),
        data: (json) {
          final vehicles = json['vehicles'] as List<dynamic>? ?? [];
          final imageUrl = json['profile_image_url']?.toString();
          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(profileProvider);
              ref.invalidate(myDriveRecordsProvider);
              ref.invalidate(myPostsProvider);
            },
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                CircleAvatar(
                  radius: 42,
                  backgroundImage: imageUrl == null ? null : NetworkImage(imageUrl),
                  child: imageUrl == null ? const Icon(Icons.person, size: 42) : null,
                ),
                const SizedBox(height: 16),
                Text(
                  json['nickname']?.toString() ?? '닉네임 미설정',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                Text(json['bio']?.toString() ?? '소개를 등록해 주세요.', textAlign: TextAlign.center),
                Text(
                  '연결 계정: ${(json['connected_accounts'] as List<dynamic>? ?? []).join(', ')}',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: () => _editProfile(context, ref, json),
                  icon: const Icon(Icons.edit_outlined),
                  label: const Text('프로필 수정'),
                ),
                if (isAdmin)
                  FilledButton.tonalIcon(
                    onPressed: () => Navigator.push(context, MaterialPageRoute(
                      builder: (_) => const AdminScreen(),
                    )),
                    icon: const Icon(Icons.admin_panel_settings_outlined),
                    label: const Text('관리자 도구'),
                  ),
                const SizedBox(height: 24),
                Row(children: [
                  Expanded(child: Text('내 차량', style: Theme.of(context).textTheme.titleMedium)),
                  TextButton.icon(onPressed: () => _addVehicle(context, ref), icon: const Icon(Icons.add), label: const Text('추가')),
                ]),
                if (vehicles.isEmpty) const ListTile(title: Text('등록한 차량이 없습니다.')),
                ...vehicles.map((raw) {
                  final vehicle = raw as Map<String, dynamic>;
                  return ListTile(
                    leading: const Icon(Icons.directions_car),
                    title: Text(vehicle['model_name'].toString()),
                    subtitle: Text('${vehicle['manufacturer'] ?? ''} ${vehicle['model_year'] ?? ''}'),
                    trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                      if (vehicle['is_primary'] == true) const Chip(label: Text('대표')),
                      IconButton(
                        onPressed: () async {
                          await ref.read(apiClientProvider).delete('/me/vehicles/${vehicle['id']}');
                          ref.invalidate(profileProvider);
                        },
                        icon: const Icon(Icons.delete_outline),
                      ),
                    ]),
                  );
                }),
                const Divider(height: 32),
                ExpansionTile(
                  leading: const Icon(Icons.history),
                  title: const Text('주행 기록'),
                  children: records.when(
                    loading: () => [const LinearProgressIndicator()],
                    error: (error, _) => [ListTile(title: Text('$error'))],
                    data: (items) => items.isEmpty
                        ? [const ListTile(title: Text('저장된 주행 기록이 없습니다.'))]
                        : items.map((item) => ListTile(
                            title: Text('주행 #${item['id']} · ${item['status']}'),
                            subtitle: Text(
                              '${((item['distance_meters'] as num) / 1000).toStringAsFixed(1)}km · '
                              '${((item['duration_seconds'] as num? ?? 0) / 60).toStringAsFixed(1)}분',
                            ),
                            trailing: item['ranking_eligible'] == true
                                ? const Chip(label: Text('랭킹 반영'))
                                : const Chip(label: Text('일반 기록')),
                          )).toList(),
                  ),
                ),
                ExpansionTile(
                  leading: const Icon(Icons.article_outlined),
                  title: const Text('작성한 글'),
                  children: posts.when(
                    loading: () => [const LinearProgressIndicator()],
                    error: (error, _) => [ListTile(title: Text('$error'))],
                    data: (items) => items.isEmpty
                        ? [const ListTile(title: Text('작성한 글이 없습니다.'))]
                        : items.map((item) => ListTile(
                            title: Text(item['content'].toString(), maxLines: 2, overflow: TextOverflow.ellipsis),
                            subtitle: Text('좋아요 ${item['like_count']} · 댓글 ${item['comment_count']}'),
                          )).toList(),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
