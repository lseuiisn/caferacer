import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/providers.dart';
import '../../sessions/presentation/session_screen.dart';

class AdminScreen extends ConsumerStatefulWidget {
  const AdminScreen({super.key});

  @override
  ConsumerState<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends ConsumerState<AdminScreen> {
  late Future<List<dynamic>> _candidates;
  late Future<List<dynamic>> _reports;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    final api = ref.read(apiClientProvider);
    _candidates = api.getAs<List<dynamic>>('/admin/cafe-imports');
    _reports = api.getAs<List<dynamic>>('/admin/reports');
  }

  Future<void> _createCandidate() async {
    final name = TextEditingController();
    final address = TextEditingController();
    final source = TextEditingController();
    final body = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('카페 수집 후보 등록'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: name,
              decoration: const InputDecoration(labelText: '카페 이름'),
            ),
            TextField(
              controller: address,
              decoration: const InputDecoration(labelText: '주소(선택)'),
            ),
            TextField(
              controller: source,
              decoration: const InputDecoration(labelText: '출처 URL(선택)'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, {
              'name': name.text.trim(),
              'address': address.text.trim().isEmpty
                  ? null
                  : address.text.trim(),
              'source_url': source.text.trim().isEmpty
                  ? null
                  : source.text.trim(),
            }),
            child: const Text('등록'),
          ),
        ],
      ),
    );
    name.dispose();
    address.dispose();
    source.dispose();
    if (body == null || (body['name'] as String).isEmpty) return;
    await ref.read(apiClientProvider).post('/admin/cafe-imports', body: body);
    setState(_reload);
  }

  Future<void> _approveCandidate(Map<String, dynamic> candidate) async {
    final address = TextEditingController(
      text: candidate['address']?.toString(),
    );
    final latitude = TextEditingController();
    final longitude = TextEditingController();
    final source = TextEditingController();
    final price = TextEditingController();
    var parking = false;
    final body = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: Text('${candidate['name']} 승인'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: address,
                  decoration: const InputDecoration(labelText: '검증 주소'),
                ),
                TextField(
                  controller: latitude,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: '위도'),
                ),
                TextField(
                  controller: longitude,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: '경도'),
                ),
                TextField(
                  controller: source,
                  decoration: const InputDecoration(labelText: '검증 출처 URL'),
                ),
                TextField(
                  controller: price,
                  decoration: const InputDecoration(labelText: '가격대(선택)'),
                ),
                SwitchListTile(
                  value: parking,
                  onChanged: (value) => setState(() => parking = value),
                  title: const Text('주차 가능'),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('취소'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, {
                'address': address.text.trim(),
                'coordinate': {
                  'latitude': double.tryParse(latitude.text),
                  'longitude': double.tryParse(longitude.text),
                },
                'source_url': source.text.trim(),
                'parking_available': parking,
                'price_range': price.text.trim().isEmpty
                    ? null
                    : price.text.trim(),
              }),
              child: const Text('승인'),
            ),
          ],
        ),
      ),
    );
    for (final controller in [address, latitude, longitude, source, price]) {
      controller.dispose();
    }
    if (body == null) return;
    try {
      await ref
          .read(apiClientProvider)
          .patch('/admin/cafe-imports/${candidate['id']}/approve', body: body);
      setState(_reload);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('$error')));
      }
    }
  }

  Future<void> _setDailyCourses() async {
    final result = await showDialog<String>(
      context: context,
      builder: (_) => const _DailyCourseDialog(),
    );
    if (result == null) return;
    final courseIds = result
        .split(',')
        .map((value) => int.tryParse(value.trim()))
        .whereType<int>()
        .take(3)
        .toList();
    if (courseIds.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('올바른 코스 ID를 입력해 주세요.')));
      }
      return;
    }
    try {
      await ref
          .read(apiClientProvider)
          .put(
            '/admin/daily-courses',
            body: {
              'recommendation_date': DateTime.now().toIso8601String().substring(
                0,
                10,
              ),
              'items': [
                for (var index = 0; index < courseIds.length; index++)
                  {
                    'course_id': courseIds[index],
                    'display_order': index + 1,
                    'headline': '오늘의 추천',
                  },
              ],
            },
          );
      ref.invalidate(dailySessionsProvider);
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('오늘의 코스를 저장했습니다.')));
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('오늘의 코스를 저장하지 못했습니다: $error')));
      }
    }
  }

  Future<void> _deactivateCourse() async {
    final controller = TextEditingController();
    final value = await showDialog<int>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('코스 비활성화'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: '코스 ID'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () =>
                Navigator.pop(context, int.tryParse(controller.text)),
            child: const Text('비활성화'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (value != null) {
      await ref.read(apiClientProvider).delete('/admin/courses/$value');
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('관리자 도구')),
    body: RefreshIndicator(
      onRefresh: () async {
        setState(_reload);
        await Future.wait([_candidates, _reports]);
      },
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton.tonalIcon(
                onPressed: _createCandidate,
                icon: const Icon(Icons.local_cafe),
                label: const Text('카페 후보 등록'),
              ),
              FilledButton.tonalIcon(
                onPressed: _setDailyCourses,
                icon: const Icon(Icons.today),
                label: const Text('오늘의 코스'),
              ),
              FilledButton.tonalIcon(
                onPressed: _deactivateCourse,
                icon: const Icon(Icons.route),
                label: const Text('코스 비활성화'),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Text('승인 대기 카페', style: Theme.of(context).textTheme.titleLarge),
          FutureBuilder<List<dynamic>>(
            future: _candidates,
            builder: (context, snapshot) => Column(
              children: (snapshot.data ?? []).map((raw) {
                final item = raw as Map<String, dynamic>;
                return ListTile(
                  title: Text(item['name'].toString()),
                  subtitle: Text(
                    item['address']?.toString() ??
                        item['search_url'].toString(),
                  ),
                  trailing: FilledButton.tonal(
                    onPressed: () => _approveCandidate(item),
                    child: const Text('검토'),
                  ),
                );
              }).toList(),
            ),
          ),
          const Divider(height: 32),
          Text('신고 관리', style: Theme.of(context).textTheme.titleLarge),
          FutureBuilder<List<dynamic>>(
            future: _reports,
            builder: (context, snapshot) => Column(
              children: (snapshot.data ?? []).map((raw) {
                final item = raw as Map<String, dynamic>;
                return ListTile(
                  title: Text(
                    '${item['target_type']} #${item['target_id']} · ${item['reason']}',
                  ),
                  subtitle: Text(item['details']?.toString() ?? ''),
                  trailing: item['status'] == 'pending'
                      ? PopupMenuButton<String>(
                          onSelected: (status) async {
                            await ref
                                .read(apiClientProvider)
                                .patch(
                                  '/admin/reports/${item['id']}',
                                  body: {'status': status},
                                );
                            setState(_reload);
                          },
                          itemBuilder: (_) => const [
                            PopupMenuItem(
                              value: 'resolved',
                              child: Text('처리 완료'),
                            ),
                            PopupMenuItem(
                              value: 'dismissed',
                              child: Text('기각'),
                            ),
                          ],
                        )
                      : Chip(label: Text(item['status'].toString())),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    ),
  );
}

class _DailyCourseDialog extends StatefulWidget {
  const _DailyCourseDialog();

  @override
  State<_DailyCourseDialog> createState() => _DailyCourseDialogState();
}

class _DailyCourseDialogState extends State<_DailyCourseDialog> {
  final _ids = TextEditingController();

  @override
  void dispose() {
    _ids.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('오늘의 코스 설정'),
    content: TextField(
      controller: _ids,
      autofocus: true,
      keyboardType: TextInputType.text,
      textInputAction: TextInputAction.done,
      onSubmitted: (_) => _save(),
      decoration: const InputDecoration(
        labelText: '코스 ID',
        helperText: '쉼표로 최대 3개 입력 (예: 1,2,3)',
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('취소'),
      ),
      FilledButton(onPressed: _save, child: const Text('저장')),
    ],
  );

  void _save() => Navigator.pop(context, _ids.text.trim());
}
