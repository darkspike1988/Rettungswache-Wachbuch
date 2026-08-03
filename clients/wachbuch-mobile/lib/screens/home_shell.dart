import 'package:flutter/material.dart';
import 'package:wachbuch_mobile/api/client.dart';
import 'package:wachbuch_mobile/screens/checklisten_screen.dart';
import 'package:wachbuch_mobile/screens/kaffeekasse_screen.dart';
import 'package:wachbuch_mobile/screens/kalender_screen.dart';
import 'package:wachbuch_mobile/ui/error_banner.dart';
import 'package:wachbuch_mobile/ui/handover_filter.dart';
import 'package:wachbuch_mobile/ui/layout.dart';
import 'package:wachbuch_mobile/ui/offline_banner.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({
    super.key,
    required this.api,
    required this.onLogout,
    required this.onChangeServer,
  });

  final WachbuchApi api;
  final Future<void> Function() onLogout;
  final Future<void> Function() onChangeServer;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _tab = 0;
  Map<String, dynamic>? _me;
  List<Map<String, dynamic>> _handovers = [];
  String? _error;
  bool _loading = true;
  bool _offline = false;
  int _reloadGeneration = 0;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    final generation = ++_reloadGeneration;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        widget.api.me(),
        widget.api.handovers(),
      ]);
      if (!mounted || generation != _reloadGeneration) {
        return;
      }
      setState(() {
        _me = results[0] as Map<String, dynamic>;
        _handovers = results[1] as List<Map<String, dynamic>>;
        _loading = false;
        _offline = false;
      });
    } on ApiException catch (error) {
      if (!mounted || generation != _reloadGeneration) {
        return;
      }
      setState(() {
        _error = error.statusCode == 401
            ? 'Anmeldung abgelaufen oder widerrufen.'
            : error.message;
        _loading = false;
        _offline = error.statusCode == 0;
      });
      if (error.statusCode == 401) {
        await widget.onLogout();
      }
    } catch (error) {
      if (!mounted || generation != _reloadGeneration) {
        return;
      }
      setState(() {
        _error = error.toString();
        _loading = false;
        _offline = true;
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
  void dispose() {
    widget.api.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final tablet = AppLayout.isTablet(width);

    final pages = IndexedStack(
      index: _tab,
      children: [
        _OverviewTab(
          api: widget.api,
          stationName: _stationName,
          roleLabel: _roleLabel,
          modules: _modules,
          handovers: _handovers,
          loading: _loading,
          hasData: _me != null,
          error: _error,
          onRefresh: _reload,
        ),
        _HandoversTab(
          api: widget.api,
          items: _handovers,
          loading: _loading,
          error: _error,
          onRefresh: _reload,
        ),
        _AccountTab(
          me: _me,
          serverUrl: widget.api.baseUrl,
          loading: _loading,
          onLogout: widget.onLogout,
          onChangeServer: widget.onChangeServer,
          onRefresh: _reload,
        ),
      ],
    );

    final appBar = AppBar(
      title: Text(_stationName, maxLines: 1, overflow: TextOverflow.ellipsis),
      actions: [
        IconButton(
          tooltip: 'Aktualisieren',
          onPressed: _loading ? null : _reload,
          icon: const Icon(Icons.refresh),
        ),
      ],
    );

    final offlineBanner = OfflineBanner(
      visible: _offline,
      onRetry: _loading ? () {} : _reload,
    );

    if (tablet) {
      return Scaffold(
        appBar: appBar,
        body: Column(
          children: [
            offlineBanner,
            Expanded(
              child: Row(
                children: [
                  NavigationRail(
                    selectedIndex: _tab,
                    onDestinationSelected: (index) =>
                        setState(() => _tab = index),
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
                  Expanded(child: pages),
                ],
              ),
            ),
          ],
        ),
      );
    }

    return Scaffold(
      appBar: appBar,
      body: Column(
        children: [offlineBanner, Expanded(child: pages)],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (index) => setState(() => _tab = index),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            label: 'Übersicht',
          ),
          NavigationDestination(
            icon: Icon(Icons.assignment_outlined),
            label: 'Übergaben',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            label: 'Konto',
          ),
        ],
      ),
    );
  }
}

class _OverviewTab extends StatelessWidget {
  const _OverviewTab({
    required this.api,
    required this.stationName,
    required this.roleLabel,
    required this.modules,
    required this.handovers,
    required this.loading,
    required this.hasData,
    required this.error,
    required this.onRefresh,
  });

  final WachbuchApi api;
  final String stationName;
  final String roleLabel;
  final Map<String, dynamic> modules;
  final List<Map<String, dynamic>> handovers;
  final bool loading;
  final bool hasData;
  final String? error;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    if (loading && !hasData) {
      return const Center(child: CircularProgressIndicator());
    }
    final width = MediaQuery.sizeOf(context).width;
    final maxW = AppLayout.contentMaxWidth(width);
    final openCount = handovers
        .where((item) => item['status'] == 'open')
        .length;
    final inProgressCount = handovers
        .where((item) => item['status'] == 'in_progress')
        .length;
    final urgentCount = handovers
        .where((item) => item['priority'] == 'urgent')
        .length;

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: maxW),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _StationHero(stationName: stationName, roleLabel: roleLabel),
              const SizedBox(height: 16),
              if (error != null) ...[
                ErrorBanner(message: error!),
                const SizedBox(height: 16),
              ],
              const _SectionTitle(
                icon: Icons.monitor_heart_outlined,
                title: 'Aktive Übergaben',
              ),
              const SizedBox(height: 12),
              LayoutBuilder(
                builder: (context, constraints) {
                  final textScale =
                      MediaQuery.textScalerOf(context).scale(14) / 14;
                  final columns = constraints.maxWidth < 360 || textScale > 1.3
                      ? 2
                      : 3;
                  final metricWidth =
                      (constraints.maxWidth - (8 * (columns - 1))) / columns;
                  return Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _DashboardMetric(
                        key: const Key('overview-stat-open'),
                        width: metricWidth,
                        icon: Icons.inbox_outlined,
                        value: openCount,
                        label: 'offen',
                      ),
                      _DashboardMetric(
                        key: const Key('overview-stat-progress'),
                        width: metricWidth,
                        icon: Icons.pending_actions_outlined,
                        value: inProgressCount,
                        label: 'in Bearbeitung',
                      ),
                      _DashboardMetric(
                        key: const Key('overview-stat-urgent'),
                        width: metricWidth,
                        icon: Icons.priority_high_rounded,
                        value: urgentCount,
                        label: 'dringend',
                        urgent: urgentCount > 0,
                      ),
                    ],
                  );
                },
              ),
              const SizedBox(height: 24),
              const _SectionTitle(
                icon: Icons.dashboard_customize_outlined,
                title: 'Module dieser Wache',
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: modules.entries.map((entry) {
                  final on = entry.value == true;
                  return Chip(
                    avatar: Icon(
                      on ? Icons.check_circle : Icons.remove_circle_outline,
                      size: 18,
                    ),
                    label: Text(moduleLabel(entry.key)),
                  );
                }).toList(),
              ),
              const SizedBox(height: 24),
              _ModuleTiles(api: api, modules: modules),
              const SizedBox(height: 24),
              Material(
                color: Theme.of(context).colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(12),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(
                        Icons.info_outline,
                        color: Theme.of(context).colorScheme.onPrimaryContainer,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'Ihre Wache und die verfügbaren Module werden automatisch '
                          'aus Ihrem Benutzerkonto geladen.',
                          style: Theme.of(context).textTheme.bodyMedium
                              ?.copyWith(
                                color: Theme.of(
                                  context,
                                ).colorScheme.onPrimaryContainer,
                              ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StationHero extends StatelessWidget {
  const _StationHero({required this.stationName, required this.roleLabel});

  final String stationName;
  final String roleLabel;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Material(
      color: scheme.primary,
      borderRadius: BorderRadius.circular(18),
      clipBehavior: Clip.antiAlias,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: scheme.onPrimary.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(
                Icons.local_hospital_outlined,
                color: scheme.onPrimary,
                size: 30,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    stationName,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(
                      context,
                    ).textTheme.titleLarge?.copyWith(color: scheme.onPrimary),
                  ),
                  if (roleLabel.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      roleLabel,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: scheme.onPrimary.withValues(alpha: 0.88),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.icon, required this.title});

  final IconData icon;
  final String title;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Row(
      children: [
        Icon(icon, size: 24, color: scheme.primary),
        const SizedBox(width: 8),
        Expanded(
          child: Text(title, style: Theme.of(context).textTheme.titleMedium),
        ),
      ],
    );
  }
}

class _DashboardMetric extends StatelessWidget {
  const _DashboardMetric({
    super.key,
    required this.width,
    required this.icon,
    required this.value,
    required this.label,
    this.urgent = false,
  });

  final double width;
  final IconData icon;
  final int value;
  final String label;
  final bool urgent;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final background = urgent ? scheme.errorContainer : scheme.surface;
    final foreground = urgent ? scheme.onErrorContainer : scheme.onSurface;
    final accent = urgent ? scheme.error : scheme.primary;
    return SizedBox(
      width: width,
      child: Card(
        color: background,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, size: 24, color: accent),
              const SizedBox(height: 10),
              Text(
                '$value $label',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: foreground,
                  height: 1.25,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ModuleTiles extends StatelessWidget {
  const _ModuleTiles({required this.api, required this.modules});

  final WachbuchApi api;
  final Map<String, dynamic> modules;

  @override
  Widget build(BuildContext context) {
    final destinations = <_ModuleDestination>[];
    if (modules['calendar'] == true) {
      destinations.add(
        const _ModuleDestination(
          key: 'module-tile-calendar',
          icon: Icons.event_outlined,
          title: 'Kalender',
          subtitle: 'Wachentermine und Dienste',
        ),
      );
    }
    if (modules['coffee'] == true) {
      destinations.add(
        const _ModuleDestination(
          key: 'module-tile-coffee',
          icon: Icons.coffee_outlined,
          title: 'Kaffeekasse',
          subtitle: 'Kassenstand und Buchungen',
        ),
      );
    }
    if (modules['checklists'] == true) {
      destinations.add(
        const _ModuleDestination(
          key: 'module-tile-checklists',
          icon: Icons.checklist_outlined,
          title: 'Checklisten',
          subtitle: 'Punkte abhaken und abschließen',
        ),
      );
    }
    if (destinations.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _SectionTitle(
          icon: Icons.apps_outlined,
          title: 'Schnellzugriff',
        ),
        const SizedBox(height: 12),
        LayoutBuilder(
          builder: (context, constraints) {
            final columns = constraints.maxWidth >= 600 ? 3 : 2;
            final tileWidth =
                (constraints.maxWidth - (8 * (columns - 1))) / columns;
            return Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final destination in destinations)
                  _ModuleTile(
                    key: Key(destination.key),
                    width: tileWidth,
                    destination: destination,
                    onTap: () => _open(context, destination),
                  ),
              ],
            );
          },
        ),
      ],
    );
  }

  void _open(BuildContext context, _ModuleDestination destination) {
    final Widget screen;
    switch (destination.key) {
      case 'module-tile-calendar':
        screen = KalenderScreen(api: api);
      case 'module-tile-coffee':
        screen = KaffeekasseScreen(api: api);
      case 'module-tile-checklists':
        screen = ChecklistenScreen(api: api);
      default:
        return;
    }
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
  }
}

class _ModuleDestination {
  const _ModuleDestination({
    required this.key,
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  final String key;
  final IconData icon;
  final String title;
  final String subtitle;
}

class _ModuleTile extends StatelessWidget {
  const _ModuleTile({
    super.key,
    required this.width,
    required this.destination,
    required this.onTap,
  });

  final double width;
  final _ModuleDestination destination;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return SizedBox(
      width: width,
      child: Card(
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(destination.icon, size: 28, color: scheme.primary),
                const SizedBox(height: 10),
                Text(
                  destination.title,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 2),
                Text(
                  destination.subtitle,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: scheme.onSurfaceVariant,
                      ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _HandoversTab extends StatefulWidget {
  const _HandoversTab({
    required this.api,
    required this.items,
    required this.loading,
    required this.error,
    required this.onRefresh,
  });

  final WachbuchApi api;
  final List<Map<String, dynamic>> items;
  final bool loading;
  final String? error;
  final Future<void> Function() onRefresh;

  @override
  State<_HandoversTab> createState() => _HandoversTabState();
}

class _HandoversTabState extends State<_HandoversTab> {
  final _searchController = TextEditingController();
  final Set<String> _statuses = {};
  final Set<String> _priorities = {};

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _toggle(Set<String> target, String value, bool selected) {
    setState(() {
      selected ? target.add(value) : target.remove(value);
    });
  }

  Future<void> _showDetails(Map<String, dynamic> item) async {
    final rawId = item['id'];
    final id = rawId is int ? rawId : int.tryParse(rawId?.toString() ?? '');
    if (id == null) {
      return;
    }
    final detailFuture = widget.api.handoverDetail(id);
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) =>
          _HandoverDetailSheet(future: detailFuture, fallback: item),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (widget.loading && widget.items.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    final width = MediaQuery.sizeOf(context).width;
    final cols = AppLayout.handoverColumns(width);
    final maxW = AppLayout.contentMaxWidth(width);
    final filtered = filterHandovers(
      widget.items,
      query: _searchController.text,
      statuses: _statuses,
      priorities: _priorities,
    );
    final availableStatuses = _orderedValues(
      [
        ...widget.items.map((item) => item['status']?.toString() ?? ''),
        ..._statuses,
      ],
      const ['open', 'in_progress', 'done'],
    );
    final availablePriorities = _orderedValues(
      [
        ...widget.items.map((item) => item['priority']?.toString() ?? ''),
        ..._priorities,
      ],
      const ['urgent', 'important', 'normal'],
    );

    return Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxW),
        child: Column(
          children: [
            if (widget.items.isNotEmpty) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                child: SearchBar(
                  key: const Key('handover-search'),
                  controller: _searchController,
                  hintText: 'Übergaben durchsuchen',
                  leading: const Icon(Icons.search),
                  trailing: [
                    if (_searchController.text.isNotEmpty)
                      IconButton(
                        tooltip: 'Suche löschen',
                        onPressed: () {
                          _searchController.clear();
                          setState(() {});
                        },
                        icon: const Icon(Icons.close),
                      ),
                  ],
                  onChanged: (_) => setState(() {}),
                ),
              ),
              _FilterSection(
                title: 'Status',
                values: availableStatuses,
                selected: _statuses,
                label: handoverStatusLabel,
                keyPrefix: 'status-filter',
                onChanged: (value, selected) =>
                    _toggle(_statuses, value, selected),
              ),
              _FilterSection(
                title: 'Priorität',
                values: availablePriorities,
                selected: _priorities,
                label: handoverPriorityLabel,
                keyPrefix: 'priority-filter',
                onChanged: (value, selected) =>
                    _toggle(_priorities, value, selected),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 6),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    '${filtered.length} von ${widget.items.length} Übergaben',
                    style: Theme.of(context).textTheme.labelLarge,
                  ),
                ),
              ),
            ],
            Expanded(
              child: RefreshIndicator(
                onRefresh: widget.onRefresh,
                child: _HandoverResults(
                  items: filtered,
                  allItemsEmpty: widget.items.isEmpty,
                  error: widget.error,
                  columns: cols,
                  onOpen: _showDetails,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FilterSection extends StatelessWidget {
  const _FilterSection({
    required this.title,
    required this.values,
    required this.selected,
    required this.label,
    required this.keyPrefix,
    required this.onChanged,
  });

  final String title;
  final List<String> values;
  final Set<String> selected;
  final String Function(Object?) label;
  final String keyPrefix;
  final void Function(String value, bool selected) onChanged;

  @override
  Widget build(BuildContext context) {
    if (values.isEmpty) {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 0, 2),
      child: Semantics(
        container: true,
        label: '$title filtern',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 6),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.only(right: 16),
              child: Row(
                children: [
                  for (final value in values)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: FilterChip(
                        key: Key('$keyPrefix-$value'),
                        label: Text(label(value)),
                        selected: selected.contains(value),
                        showCheckmark: true,
                        onSelected: (active) => onChanged(value, active),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HandoverResults extends StatelessWidget {
  const _HandoverResults({
    required this.items,
    required this.allItemsEmpty,
    required this.error,
    required this.columns,
    required this.onOpen,
  });

  final List<Map<String, dynamic>> items;
  final bool allItemsEmpty;
  final String? error;
  final int columns;
  final void Function(Map<String, dynamic> item) onOpen;

  @override
  Widget build(BuildContext context) {
    if (error != null && allItemsEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [ErrorBanner(message: error!)],
      );
    }
    if (allItemsEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: const [Text('Keine aktiven Übergaben.')],
      );
    }
    if (items.isEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: const [Text('Keine Übergaben für diese Filter.')],
      );
    }
    if (columns == 1) {
      return ListView.separated(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(12, 4, 12, 16),
        itemCount: items.length,
        separatorBuilder: (_, _) => const SizedBox(height: 4),
        itemBuilder: (context, index) =>
            _HandoverCard(item: items[index], onOpen: onOpen),
      );
    }
    return GridView.builder(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(12, 4, 12, 16),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: columns,
        mainAxisExtent: _handoverCardExtent(context),
        crossAxisSpacing: 8,
        mainAxisSpacing: 8,
      ),
      itemCount: items.length,
      itemBuilder: (context, index) =>
          _HandoverCard(item: items[index], onOpen: onOpen),
    );
  }
}

class _HandoverCard extends StatelessWidget {
  const _HandoverCard({required this.item, required this.onOpen});

  final Map<String, dynamic> item;
  final void Function(Map<String, dynamic> item) onOpen;

  @override
  Widget build(BuildContext context) {
    final title = item['title']?.toString().trim();
    return Semantics(
      button: true,
      label:
          'Übergabe ${title?.isNotEmpty == true ? title : 'ohne Titel'} öffnen',
      child: SizedBox(
        height: _handoverCardExtent(context),
        child: Card(
          margin: const EdgeInsets.all(4),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: () => onOpen(item),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Container(
                  width: 5,
                  color: _priorityColors(context, item['priority']).foreground,
                ),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title?.isNotEmpty == true ? title! : 'Übergabe',
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 6),
                        Text(
                          handoverCategoryLabel(item['category']),
                          style: Theme.of(context).textTheme.bodyMedium
                              ?.copyWith(
                                color: Theme.of(
                                  context,
                                ).colorScheme.onSurfaceVariant,
                              ),
                        ),
                        const Spacer(),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            _HandoverChip(
                              label: handoverStatusLabel(item['status']),
                              colors: _statusColors(context, item['status']),
                            ),
                            _HandoverChip(
                              label: handoverPriorityLabel(item['priority']),
                              colors: _priorityColors(
                                context,
                                item['priority'],
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _HandoverChip extends StatelessWidget {
  const _HandoverChip({required this.label, required this.colors});

  final String label;
  final ({Color background, Color foreground}) colors;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: colors.background,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: colors.foreground,
          fontSize: 14,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _HandoverDetailSheet extends StatelessWidget {
  const _HandoverDetailSheet({required this.future, required this.fallback});

  final Future<Map<String, dynamic>> future;
  final Map<String, dynamic> fallback;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: FutureBuilder<Map<String, dynamic>>(
        future: future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const SizedBox(
              height: 240,
              child: Center(child: CircularProgressIndicator()),
            );
          }
          if (snapshot.hasError) {
            final message = snapshot.error is ApiException
                ? (snapshot.error! as ApiException).message
                : 'Details konnten nicht geladen werden.';
            return Padding(
              padding: const EdgeInsets.all(24),
              child: ErrorBanner(message: message),
            );
          }
          final item = {...fallback, ...?snapshot.data};
          final rawAuthor = item['author'];
          final author = rawAuthor is Map ? rawAuthor : null;
          final authorName = author?['display_name']?.toString();
          final details = item['details']?.toString().trim();
          final version = item['version'];
          return SingleChildScrollView(
            padding: EdgeInsets.fromLTRB(
              24,
              0,
              24,
              24 + MediaQuery.viewInsetsOf(context).bottom,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item['title']?.toString() ?? 'Übergabe',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _HandoverChip(
                      label: handoverCategoryLabel(item['category']),
                      colors: (
                        background: Theme.of(
                          context,
                        ).colorScheme.surfaceContainerHighest,
                        foreground: Theme.of(context).colorScheme.onSurface,
                      ),
                    ),
                    _HandoverChip(
                      label: handoverStatusLabel(item['status']),
                      colors: _statusColors(context, item['status']),
                    ),
                    _HandoverChip(
                      label: handoverPriorityLabel(item['priority']),
                      colors: _priorityColors(context, item['priority']),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                Text(
                  details?.isNotEmpty == true
                      ? details!
                      : 'Keine weiteren Angaben.',
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: 20),
                if (authorName?.isNotEmpty == true)
                  _DetailRow(icon: Icons.person_outline, value: authorName!),
                if (item['updated_at'] != null)
                  _DetailRow(
                    icon: Icons.update,
                    value:
                        'Aktualisiert ${_formatTimestamp(item['updated_at'])}',
                  ),
                if (version != null)
                  _DetailRow(icon: Icons.history, value: 'Version $version'),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.icon, required this.value});

  final IconData icon;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(icon, size: 24, color: Theme.of(context).colorScheme.primary),
          const SizedBox(width: 8),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}

List<String> _orderedValues(Iterable<String> values, List<String> order) {
  final available = values.where((value) => value.isNotEmpty).toSet();
  final result = order.where(available.remove).toList();
  final unknown = available.toList()..sort();
  return [...result, ...unknown];
}

double _handoverCardExtent(BuildContext context) {
  final scale = MediaQuery.textScalerOf(context).scale(1);
  final extraScale = (scale - 1).clamp(0.0, 2.0);
  return 196 + (190 * extraScale);
}

({Color background, Color foreground}) _statusColors(
  BuildContext context,
  Object? status,
) {
  final colors = Theme.of(context).colorScheme;
  return switch (status?.toString()) {
    'open' => (
      background: colors.primaryContainer,
      foreground: colors.onPrimaryContainer,
    ),
    'in_progress' => (
      background: colors.secondaryContainer,
      foreground: colors.onSecondaryContainer,
    ),
    'done' => (
      background: colors.surfaceContainerHighest,
      foreground: colors.onSurface,
    ),
    _ => (
      background: colors.surfaceContainerHigh,
      foreground: colors.onSurface,
    ),
  };
}

({Color background, Color foreground}) _priorityColors(
  BuildContext context,
  Object? priority,
) {
  final colors = Theme.of(context).colorScheme;
  return switch (priority?.toString()) {
    'urgent' => (
      background: colors.errorContainer,
      foreground: colors.onErrorContainer,
    ),
    'important' => (
      background: colors.tertiaryContainer,
      foreground: colors.onTertiaryContainer,
    ),
    _ => (
      background: colors.surfaceContainerHighest,
      foreground: colors.onSurface,
    ),
  };
}

String _formatTimestamp(Object? value) {
  final parsed = DateTime.tryParse(value?.toString() ?? '')?.toLocal();
  if (parsed == null) {
    return value?.toString() ?? '—';
  }
  String two(int number) => number.toString().padLeft(2, '0');
  return '${two(parsed.day)}.${two(parsed.month)}.${parsed.year}, '
      '${two(parsed.hour)}:${two(parsed.minute)} Uhr';
}

class _AccountTab extends StatelessWidget {
  const _AccountTab({
    required this.me,
    required this.serverUrl,
    required this.loading,
    required this.onLogout,
    required this.onChangeServer,
    required this.onRefresh,
  });

  final Map<String, dynamic>? me;
  final String serverUrl;
  final bool loading;
  final Future<void> Function() onLogout;
  final Future<void> Function() onChangeServer;
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
              onPressed: loading ? null : onRefresh,
              child: const Text('Profil aktualisieren'),
            ),
            const SizedBox(height: 8),
            FilledButton.tonal(
              onPressed: loading ? null : onLogout,
              child: const Text('Abmelden'),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: loading ? null : onChangeServer,
              child: const Text('Anderen Server einrichten'),
            ),
          ],
        ),
      ),
    );
  }
}
