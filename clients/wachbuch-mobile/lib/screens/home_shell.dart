import 'package:flutter/material.dart';
import 'package:wachbuch_mobile/api/client.dart';
import 'package:wachbuch_mobile/ui/layout.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({
    super.key,
    required this.api,
    required this.onLogout,
  });

  final WachbuchApi api;
  final Future<void> Function() onLogout;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _tab = 0;
  Map<String, dynamic>? _me;
  List<Map<String, dynamic>> _handovers = [];
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final me = await widget.api.me();
      final handovers = await widget.api.handovers();
      if (!mounted) {
        return;
      }
      setState(() {
        _me = me;
        _handovers = handovers;
        _loading = false;
      });
    } on ApiException catch (error) {
      setState(() {
        _error = error.message;
        _loading = false;
      });
      if (error.statusCode == 401) {
        await widget.onLogout();
      }
    } catch (error) {
      setState(() {
        _error = error.toString();
        _loading = false;
      });
    }
  }

  String get _stationName {
    final station = (_me?['membership'] as Map?)?['station'] as Map?;
    return (station?['name'] as String?) ?? 'Wachbuch';
  }

  String get _roleLabel {
    final membership = _me?['membership'] as Map?;
    return (membership?['role_label'] as String?) ?? '';
  }

  Map<String, dynamic> get _modules {
    final station = (_me?['membership'] as Map?)?['station'] as Map?;
    final modules = station?['modules'];
    if (modules is Map<String, dynamic>) {
      return modules;
    }
    if (modules is Map) {
      return Map<String, dynamic>.from(modules);
    }
    return {};
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final tablet = AppLayout.isTablet(width);

    final pages = [
      _OverviewTab(
        stationName: _stationName,
        roleLabel: _roleLabel,
        modules: _modules,
        handoverCount: _handovers.length,
        loading: _loading,
        error: _error,
        onRefresh: _reload,
      ),
      _HandoversTab(
        items: _handovers,
        loading: _loading,
        error: _error,
        onRefresh: _reload,
      ),
      _AccountTab(
        me: _me,
        serverUrl: widget.api.baseUrl,
        onLogout: widget.onLogout,
        onRefresh: _reload,
      ),
    ];

    final appBar = AppBar(
      title: Text(_stationName),
      actions: [
        IconButton(
          tooltip: 'Aktualisieren',
          onPressed: _loading ? null : _reload,
          icon: const Icon(Icons.refresh),
        ),
      ],
    );

    if (tablet) {
      return Scaffold(
        appBar: appBar,
        body: Row(
          children: [
            NavigationRail(
              selectedIndex: _tab,
              onDestinationSelected: (index) => setState(() => _tab = index),
              labelType: width >= AppLayout.wideBreakpoint
                  ? NavigationRailLabelType.all
                  : NavigationRailLabelType.selected,
              destinations: const [
                NavigationRailDestination(
                  icon: Icon(Icons.home_outlined),
                  selectedIcon: Icon(Icons.home),
                  label: Text('Übersicht'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.assignment_outlined),
                  selectedIcon: Icon(Icons.assignment),
                  label: Text('Übergaben'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.person_outline),
                  selectedIcon: Icon(Icons.person),
                  label: Text('Konto'),
                ),
              ],
            ),
            const VerticalDivider(width: 1),
            Expanded(child: pages[_tab]),
          ],
        ),
      );
    }

    return Scaffold(
      appBar: appBar,
      body: pages[_tab],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (index) => setState(() => _tab = index),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), label: 'Übersicht'),
          NavigationDestination(icon: Icon(Icons.assignment_outlined), label: 'Übergaben'),
          NavigationDestination(icon: Icon(Icons.person_outline), label: 'Konto'),
        ],
      ),
    );
  }
}

class _OverviewTab extends StatelessWidget {
  const _OverviewTab({
    required this.stationName,
    required this.roleLabel,
    required this.modules,
    required this.handoverCount,
    required this.loading,
    required this.error,
    required this.onRefresh,
  });

  final String stationName;
  final String roleLabel;
  final Map<String, dynamic> modules;
  final int handoverCount;
  final bool loading;
  final String? error;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    if (loading && stationName == 'Wachbuch') {
      return const Center(child: CircularProgressIndicator());
    }
    final width = MediaQuery.sizeOf(context).width;
    final maxW = AppLayout.contentMaxWidth(width);

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: maxW),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(stationName, style: Theme.of(context).textTheme.headlineSmall),
              if (roleLabel.isNotEmpty)
                Text(roleLabel, style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 16),
              if (error != null)
                Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.assignment),
                title: const Text('Aktive Übergaben'),
                trailing: Text('$handoverCount'),
              ),
              const SizedBox(height: 8),
              Text('Module dieser Wache', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: modules.entries.map((entry) {
                  final on = entry.value == true;
                  return FilterChip(
                    label: Text(entry.key),
                    selected: on,
                    onSelected: null,
                  );
                }).toList(),
              ),
              const SizedBox(height: 24),
              Text(
                'Wachenspezifisch: Die Station kommt aus GET /api/v1/me/. '
                'Es gibt keine freie Wachenauswahl in der App.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HandoversTab extends StatelessWidget {
  const _HandoversTab({
    required this.items,
    required this.loading,
    required this.error,
    required this.onRefresh,
  });

  final List<Map<String, dynamic>> items;
  final bool loading;
  final String? error;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    if (loading && items.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    final width = MediaQuery.sizeOf(context).width;
    final cols = AppLayout.handoverColumns(width);
    final maxW = AppLayout.contentMaxWidth(width);

    Widget tile(Map<String, dynamic> item) {
      return Card(
        margin: const EdgeInsets.all(4),
        child: ListTile(
          title: Text((item['title'] as String?) ?? 'Übergabe'),
          subtitle: Text(
            '${item['priority'] ?? ''} · ${item['status'] ?? ''} · ${item['category'] ?? ''}',
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: maxW),
          child: Builder(
            builder: (context) {
              if (error != null && items.isEmpty) {
                return ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(16),
                  children: [
                    Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                  ],
                );
              }
              if (items.isEmpty) {
                return ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(16),
                  children: const [Text('Keine aktiven Übergaben.')],
                );
              }
              if (cols == 1) {
                return ListView.separated(
                  padding: const EdgeInsets.all(12),
                  itemCount: items.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 4),
                  itemBuilder: (context, index) => tile(items[index]),
                );
              }
              return GridView.builder(
                padding: const EdgeInsets.all(12),
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: cols,
                  mainAxisExtent: 96,
                  crossAxisSpacing: 8,
                  mainAxisSpacing: 8,
                ),
                itemCount: items.length,
                itemBuilder: (context, index) => tile(items[index]),
              );
            },
          ),
        ),
      ),
    );
  }
}

class _AccountTab extends StatelessWidget {
  const _AccountTab({
    required this.me,
    required this.serverUrl,
    required this.onLogout,
    required this.onRefresh,
  });

  final Map<String, dynamic>? me;
  final String serverUrl;
  final Future<void> Function() onLogout;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final user = me?['user'] as Map?;
    final width = MediaQuery.sizeOf(context).width;
    final maxW = AppLayout.contentMaxWidth(width);

    return Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxW),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Angemeldet als'),
              subtitle: Text((user?['username'] as String?) ?? '—'),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Server'),
              subtitle: Text(serverUrl),
            ),
            const ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text('Lizenz'),
              subtitle: Text('AGPL-3.0-or-later · Quellcode offen'),
            ),
            const SizedBox(height: 12),
            OutlinedButton(
              onPressed: onRefresh,
              child: const Text('Profil aktualisieren'),
            ),
            const SizedBox(height: 8),
            FilledButton.tonal(
              onPressed: onLogout,
              child: const Text('Abmelden (Token löschen)'),
            ),
          ],
        ),
      ),
    );
  }
}
