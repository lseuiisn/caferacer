import '../domain/cafe.dart';

class CafeListState {
  final List<Cafe> cafes;
  final int page;
  final int pageSize;
  final int total;
  final bool isLoading;
  final bool isLoadingMore;
  final String? errorMessage;

  const CafeListState({
    this.cafes = const [],
    this.page = 1,
    this.pageSize = 20,
    this.total = 0,
    this.isLoading = false,
    this.isLoadingMore = false,
    this.errorMessage,
  });

  bool get hasMore => cafes.length < total;

  CafeListState copyWith({
    List<Cafe>? cafes,
    int? page,
    int? total,
    bool? isLoading,
    bool? isLoadingMore,
    String? errorMessage,
    bool clearError = false,
  }) {
    return CafeListState(
      cafes: cafes ?? this.cafes,
      page: page ?? this.page,
      pageSize: pageSize,
      total: total ?? this.total,
      isLoading: isLoading ?? this.isLoading,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }
}
