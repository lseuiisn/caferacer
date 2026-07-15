import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/providers.dart';
import '../../courses/presentation/lightning_course_form.dart';
import '../../drive_tracking/presentation/drive_session_screen.dart';
import '../../navigation/domain/navigation_gateway.dart';
import '../../rankings/presentation/ranking_sheet.dart';

final crewsProvider = FutureProvider.autoDispose<List<dynamic>>((ref) async {
  final json = await ref.watch(apiClientProvider).get('/crews');
  return (json as Map<String, dynamic>)['items'] as List<dynamic>;
});

class CrewScreen extends ConsumerWidget {
  const CrewScreen({super.key});

  Future<void> _createCrew(BuildContext context, WidgetRef ref) async {
    final name = TextEditingController();
    final description = TextEditingController();
    var visibility = 'public';
    var joinPolicy = 'open';
    final result = await showDialog<Map<String, String>>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('크루 만들기'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TextField(controller: name, decoration: const InputDecoration(labelText: '크루 이름')),
              TextField(
                controller: description,
                decoration: const InputDecoration(labelText: '소개'),
                maxLines: 3,
              ),
              DropdownButtonFormField<String>(
                initialValue: visibility,
                decoration: const InputDecoration(labelText: '공개 설정'),
                items: const [
                  DropdownMenuItem(value: 'public', child: Text('공개')),
                  DropdownMenuItem(value: 'private', child: Text('비공개')),
                ],
                onChanged: (value) => setState(() => visibility = value!),
              ),
              DropdownButtonFormField<String>(
                initialValue: joinPolicy,
                decoration: const InputDecoration(labelText: '가입 방식'),
                items: const [
                  DropdownMenuItem(value: 'open', child: Text('즉시 가입')),
                  DropdownMenuItem(value: 'approval', child: Text('가입 승인')),
                  DropdownMenuItem(value: 'invite_only', child: Text('초대 전용')),
                ],
                onChanged: (value) => setState(() => joinPolicy = value!),
              ),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context), child: const Text('취소')),
            FilledButton(
              onPressed: () => Navigator.pop(context, {
                'name': name.text.trim(),
                'description': description.text.trim(),
                'visibility': visibility,
                'join_policy': joinPolicy,
              }),
              child: const Text('생성'),
            ),
          ],
        ),
      ),
    );
    name.dispose();
    description.dispose();
    if (result == null || result['name']!.length < 2 || !context.mounted) return;
    try {
      await ref.read(apiClientProvider).post('/crews', body: result);
      ref.invalidate(crewsProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('크루를 만들었습니다.')));
      }
    } catch (error) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
    }
  }

  Future<void> _acceptInvite(BuildContext context, WidgetRef ref) async {
    final controller = TextEditingController();
    final token = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('초대 코드로 가입'),
        content: TextField(controller: controller, decoration: const InputDecoration(labelText: '초대 코드')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('취소')),
          FilledButton(onPressed: () => Navigator.pop(context, controller.text.trim()), child: const Text('가입')),
        ],
      ),
    );
    controller.dispose();
    if (token == null || token.isEmpty) return;
    try {
      await ref.read(apiClientProvider).post('/crews/invitations/accept', body: {'token': token});
      ref.invalidate(crewsProvider);
    } catch (error) {
      if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final crews = ref.watch(crewsProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('크루'),
        actions: [
          IconButton(
            tooltip: '초대 코드로 가입',
            onPressed: () => _acceptInvite(context, ref),
            icon: const Icon(Icons.vpn_key_outlined),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _createCrew(context, ref),
        icon: const Icon(Icons.group_add),
        label: const Text('크루 만들기'),
      ),
      body: crews.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(child: Text('$error')),
        data: (items) => RefreshIndicator(
          onRefresh: () => ref.refresh(crewsProvider.future),
          child: ListView.builder(
            itemCount: items.isEmpty ? 1 : items.length,
            itemBuilder: (context, index) {
              if (items.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(child: Text('참여 가능한 크루가 없습니다.')),
                );
              }
              final crew = items[index] as Map<String, dynamic>;
              final joined = crew['my_status'] == 'active';
              final pending = crew['my_status'] == 'pending';
              return ListTile(
                leading: const CircleAvatar(child: Icon(Icons.groups)),
                title: Text(crew['name'].toString()),
                subtitle: Text('${crew['member_count']}명 · ${crew['description'] ?? ''}'),
                onTap: joined
                    ? () => Navigator.push(context, MaterialPageRoute(
                          builder: (_) => CrewDetailScreen(crew: crew),
                        ))
                    : null,
                trailing: joined
                    ? const Icon(Icons.chevron_right)
                    : pending
                        ? const Chip(label: Text('승인 대기'))
                        : FilledButton.tonal(
                            onPressed: () async {
                              try {
                                await ref.read(apiClientProvider).post('/crews/${crew['id']}/join');
                                ref.invalidate(crewsProvider);
                              } catch (error) {
                                if (context.mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
                                }
                              }
                            },
                            child: const Text('가입'),
                          ),
              );
            },
          ),
        ),
      ),
    );
  }
}

class CrewDetailScreen extends ConsumerStatefulWidget {
  const CrewDetailScreen({required this.crew, super.key});

  final Map<String, dynamic> crew;

  @override
  ConsumerState<CrewDetailScreen> createState() => _CrewDetailScreenState();
}

class _CrewDetailScreenState extends ConsumerState<CrewDetailScreen> {
  late Future<List<dynamic>> _messages;
  late Future<List<dynamic>> _courses;
  late Future<List<dynamic>> _members;
  late Future<List<dynamic>> _dailyRankings;
  final _message = TextEditingController();

  int get _crewId => widget.crew['id'] as int;
  int get _myUserId => int.parse(ref.read(authControllerProvider).session!.userId);

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  void dispose() {
    _message.dispose();
    super.dispose();
  }

  void _reload() {
    final api = ref.read(apiClientProvider);
    _messages = api.getAs<List<dynamic>>('/crews/$_crewId/messages');
    _courses = api.getAs<List<dynamic>>('/crews/$_crewId/courses');
    _members = api.getAs<List<dynamic>>('/crews/$_crewId/members');
    _dailyRankings = api.getAs<List<dynamic>>('/crews/$_crewId/daily-rankings');
  }

  Future<void> _refresh() async {
    setState(_reload);
    await Future.wait([_messages, _courses, _members, _dailyRankings]);
  }

  Future<void> _send() async {
    final content = _message.text.trim();
    if (content.isEmpty) return;
    try {
      await ref.read(apiClientProvider).post('/crews/$_crewId/messages', body: {'content': content});
      _message.clear();
      setState(_reload);
    } catch (error) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
    }
  }

  Future<void> _createInvitation() async {
    try {
      final json = await ref.read(apiClientProvider).post('/crews/$_crewId/invitations')
          as Map<String, dynamic>;
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('초대 코드'),
          content: SelectableText(json['token'].toString()),
          actions: [FilledButton(onPressed: () => Navigator.pop(context), child: const Text('확인'))],
        ),
      );
    } catch (error) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
    }
  }

  Future<void> _configureDailyRanking() async {
    final courseId = TextEditingController();
    final baseline = TextEditingController();
    var mode = 'fastest';
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => StatefulBuilder(builder: (context, setState) => AlertDialog(
        title: const Text('오늘의 코스 크루 랭킹'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(
            controller: courseId,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: '오늘의 코스 ID'),
          ),
          DropdownButtonFormField<String>(
            initialValue: mode,
            items: const [
              DropdownMenuItem(value: 'fastest', child: Text('시간이 짧은 순')),
              DropdownMenuItem(value: 'closest_to_baseline', child: Text('기준 시간에 가까운 순')),
            ],
            onChanged: (value) => setState(() => mode = value!),
          ),
          TextField(
            controller: baseline,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: '기준 시간(분, 선택)'),
          ),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('취소')),
          FilledButton(onPressed: () => Navigator.pop(context, {
            'course_id': int.tryParse(courseId.text),
            'ranking_mode': mode,
            'baseline_duration_seconds': int.tryParse(baseline.text) == null
                ? null
                : int.parse(baseline.text) * 60,
            'recommendation_date': DateTime.now().toIso8601String().substring(0, 10),
          }), child: const Text('저장')),
        ],
      )),
    );
    courseId.dispose();
    baseline.dispose();
    if (result == null || result['course_id'] == null) return;
    try {
      await ref.read(apiClientProvider).put('/crews/$_crewId/daily-rankings', body: result);
      setState(_reload);
    } catch (error) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<dynamic>>(
      future: _members,
      builder: (context, snapshot) {
        final members = snapshot.data ?? [];
        final me = members.cast<Map<String, dynamic>>().where(
          (member) => member['user_id'] == _myUserId,
        ).firstOrNull;
        final isManager = me?['role'] == 'owner' || me?['role'] == 'manager';
        return Scaffold(
          appBar: AppBar(
            title: Text(widget.crew['name'].toString()),
            actions: [
              if (isManager)
                PopupMenuButton<String>(
                  onSelected: (value) async {
                    if (value == 'invite') await _createInvitation();
                    if (value == 'daily') await _configureDailyRanking();
                    if (value == 'lightning') {
                      if (!context.mounted) return;
                      final created = await Navigator.push<bool>(context, MaterialPageRoute(
                        builder: (_) => LightningCourseForm(crewId: _crewId),
                      ));
                      if (created == true && mounted) setState(_reload);
                    }
                  },
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'lightning', child: Text('크루 번개 만들기')),
                    PopupMenuItem(value: 'daily', child: Text('오늘의 코스 랭킹 설정')),
                    PopupMenuItem(value: 'invite', child: Text('초대 코드 만들기')),
                  ],
                ),
            ],
          ),
          body: RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(widget.crew['description']?.toString() ?? ''),
                const SizedBox(height: 20),
                Text('크루원', style: Theme.of(context).textTheme.titleMedium),
                ...members.map((raw) {
                  final member = raw as Map<String, dynamic>;
                  return ListTile(
                    leading: const Icon(Icons.person_outline),
                    title: Text(member['nickname']?.toString() ?? '사용자'),
                    subtitle: Text('${member['role']} · ${member['status']}'),
                    trailing: isManager && member['status'] == 'pending'
                        ? FilledButton.tonal(
                            onPressed: () async {
                              await ref.read(apiClientProvider).patch(
                                '/crews/$_crewId/members/${member['user_id']}/approve',
                              );
                              setState(_reload);
                            },
                            child: const Text('승인'),
                          )
                        : null,
                  );
                }),
                const Divider(height: 32),
                Text('오늘의 코스 크루 랭킹', style: Theme.of(context).textTheme.titleMedium),
                FutureBuilder<List<dynamic>>(
                  future: _dailyRankings,
                  builder: (context, snapshot) {
                    final rankings = snapshot.data ?? [];
                    if (rankings.isEmpty) return const ListTile(title: Text('크루장이 설정한 랭킹이 없습니다.'));
                    return Column(children: rankings.map((raw) {
                      final item = raw as Map<String, dynamic>;
                      return ListTile(
                        leading: const Icon(Icons.emoji_events_outlined),
                        title: Text('코스 #${item['course_id']}'),
                        subtitle: Text(item['ranking_mode'].toString()),
                        onTap: () => showModalBottomSheet<void>(
                          context: context,
                          showDragHandle: true,
                          builder: (_) => RankingSheet.custom(
                            path: '/crews/$_crewId/daily-rankings/${item['course_id']}',
                          ),
                        ),
                      );
                    }).toList());
                  },
                ),
                const Divider(height: 32),
                Text('크루 번개코스', style: Theme.of(context).textTheme.titleMedium),
                FutureBuilder<List<dynamic>>(
                  future: _courses,
                  builder: (context, snapshot) {
                    final courses = snapshot.data ?? [];
                    if (courses.isEmpty) return const ListTile(title: Text('오늘 진행하는 크루 번개가 없습니다.'));
                    return Column(children: courses.map((raw) {
                      final course = raw as Map<String, dynamic>;
                      return ListTile(
                        leading: const Icon(Icons.bolt),
                        title: Text(course['name'].toString()),
                        subtitle: Text('${course['start_name']} → ${course['destination_name']}'),
                        onTap: () => _showCrewCourse(course),
                      );
                    }).toList());
                  },
                ),
                const Divider(height: 32),
                Text('크루 채팅', style: Theme.of(context).textTheme.titleMedium),
                FutureBuilder<List<dynamic>>(
                  future: _messages,
                  builder: (context, snapshot) => Column(
                    children: (snapshot.data ?? []).map((raw) {
                      final message = raw as Map<String, dynamic>;
                      return ListTile(
                        title: Text(message['author_nickname']?.toString() ?? '사용자'),
                        subtitle: Text(message['content'].toString()),
                      );
                    }).toList(),
                  ),
                ),
                Row(children: [
                  Expanded(child: TextField(
                    controller: _message,
                    decoration: const InputDecoration(hintText: '메시지 입력'),
                  )),
                  IconButton(onPressed: _send, icon: const Icon(Icons.send)),
                ]),
              ],
            ),
          ),
        );
      },
    );
  }

  void _showCrewCourse(Map<String, dynamic> course) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) => Padding(
        padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(course['name'].toString(), style: Theme.of(context).textTheme.titleLarge),
          Text('${course['start_name']} → ${course['destination_name']}'),
          Text('진행일 ${course['event_date']}'),
          const SizedBox(height: 16),
          Row(children: [
            Expanded(child: OutlinedButton(
              onPressed: () => showModalBottomSheet<void>(
                context: context,
                showDragHandle: true,
                builder: (_) => RankingSheet.crewCourse(crewCourseId: course['id'] as int),
              ),
              child: const Text('랭킹 보기'),
            )),
            const SizedBox(width: 8),
            Expanded(child: FilledButton(
              onPressed: () {
                final start = course['start'] as Map<String, dynamic>;
                Navigator.pop(sheetContext);
                startDriveFlow(context, ref, DriveTarget(
                  name: course['name'].toString(),
                  crewCourseId: course['id'] as int,
                  start: NavigationPoint(
                    name: course['start_name'].toString(),
                    latitude: (start['latitude'] as num).toDouble(),
                    longitude: (start['longitude'] as num).toDouble(),
                  ),
                ));
              },
              child: const Text('주행 시작'),
            )),
          ]),
        ]),
      ),
    );
  }
}
