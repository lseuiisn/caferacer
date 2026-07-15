class PageMeta {
  final int page;
  final int size;
  final int total;

  const PageMeta({required this.page, required this.size, required this.total});

  factory PageMeta.fromJson(Map<String, dynamic> json) => PageMeta(
    page: json['page'] as int,
    size: json['size'] as int,
    total: json['total'] as int,
  );
}
