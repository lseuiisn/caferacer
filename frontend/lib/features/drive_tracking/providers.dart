import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/providers.dart';
import 'data/drive_tracking_service.dart';

final driveTrackingServiceProvider = Provider<DriveTrackingService>((ref) {
  final service = DriveTrackingService(ref.watch(apiClientProvider));
  ref.onDispose(service.dispose);
  return service;
});
