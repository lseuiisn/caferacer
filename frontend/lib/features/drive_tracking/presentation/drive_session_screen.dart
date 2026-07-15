import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';

import '../../navigation/data/tmap_navigation_gateway.dart';
import '../../navigation/domain/navigation_gateway.dart';
import '../providers.dart';

class DriveTarget {
  const DriveTarget({
    required this.name,
    required this.start,
    this.courseId,
    this.crewCourseId,
    this.lightningCourseId,
  });

  final String name;
  final NavigationPoint start;
  final int? courseId;
  final int? crewCourseId;
  final int? lightningCourseId;
}

Future<void> startDriveFlow(
  BuildContext context,
  WidgetRef ref,
  DriveTarget target,
) async {
  final service = ref.read(driveTrackingServiceProvider);
  try {
    final origin = await service.currentPosition();
    await service.start(
      courseId: target.courseId,
      crewCourseId: target.crewCourseId,
      lightningCourseId: target.lightningCourseId,
    );
    if (!context.mounted) return;
    unawaited(Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => DriveSessionScreen(title: target.name),
    )));
    try {
      await TmapNavigationGateway().startGuidance(
        origin: NavigationPoint(
          latitude: origin.latitude,
          longitude: origin.longitude,
        ),
        destination: target.start,
      );
    } catch (error) {
      await service.cancel();
      if (context.mounted) {
        Navigator.of(context).popUntil((route) => route.isFirst);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$error')),
        );
      }
    }
  } catch (error) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$error')),
      );
    }
  }
}

class DriveSessionScreen extends ConsumerStatefulWidget {
  const DriveSessionScreen({required this.title, super.key});

  final String title;

  @override
  ConsumerState<DriveSessionScreen> createState() => _DriveSessionScreenState();
}

class _DriveSessionScreenState extends ConsumerState<DriveSessionScreen> {
  late final DateTime _startedAt = DateTime.now();
  late final Timer _timer;
  Position? _position;
  StreamSubscription<Position>? _positionSubscription;
  bool _finishing = false;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
    _positionSubscription = ref.read(driveTrackingServiceProvider).positions.listen(
      (position) => mounted ? setState(() => _position = position) : null,
    );
  }

  @override
  void dispose() {
    _timer.cancel();
    _positionSubscription?.cancel();
    super.dispose();
  }

  String get _elapsed {
    final seconds = DateTime.now().difference(_startedAt).inSeconds;
    final hours = seconds ~/ 3600;
    final minutes = (seconds % 3600) ~/ 60;
    final remain = seconds % 60;
    return '${hours.toString().padLeft(2, '0')}:'
        '${minutes.toString().padLeft(2, '0')}:'
        '${remain.toString().padLeft(2, '0')}';
  }

  Future<void> _complete() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('주행을 종료할까요?'),
        content: const Text('수집된 GPS 경로를 검증한 뒤 랭킹 반영 여부를 알려드립니다.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('계속 주행')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('주행 종료')),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() => _finishing = true);
    try {
      final result = await ref.read(driveTrackingServiceProvider).complete();
      if (!mounted) return;
      final valid = result['ranking_eligible'] == true;
      await showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (context) => AlertDialog(
          icon: Icon(valid ? Icons.emoji_events : Icons.info_outline),
          title: Text(valid ? '완주가 확인되었습니다' : '주행 기록이 저장되었습니다'),
          content: Text(valid
              ? 'GPS 경로 검증을 통과해 랭킹에 반영됩니다.'
              : '출발지·목적지 또는 코스 통과 기준을 충족하지 않아 랭킹에는 반영되지 않습니다.'),
          actions: [FilledButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('확인'),
          )],
        ),
      );
      if (mounted) Navigator.pop(context, result);
    } catch (error) {
      if (mounted) {
        setState(() => _finishing = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final speed = ((_position?.speed ?? 0).clamp(0, 1000) * 3.6);
    return PopScope(
      canPop: false,
      child: Scaffold(
        appBar: AppBar(title: const Text('주행 기록 중'), automaticallyImplyLeading: false),
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(widget.title, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 32),
                Text(_elapsed, textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.displayMedium),
                const SizedBox(height: 16),
                Text('${speed.toStringAsFixed(0)} km/h', textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.headlineMedium),
                const SizedBox(height: 24),
                const Card(child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Text('안전을 위해 운전 중에는 화면을 조작하지 마세요.\n'
                      '기준보다 빠른 기록은 파란색, 느린 기록은 빨간색으로 표시되며 랭킹은 합의된 순위를 유지합니다.'),
                )),
                const Spacer(),
                FilledButton.icon(
                  onPressed: _finishing ? null : _complete,
                  icon: _finishing
                      ? const SizedBox.square(dimension: 18, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.stop_circle_outlined),
                  label: const Text('주행 종료'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
