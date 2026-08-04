import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:wachbuch_mobile/ui/status_chip.dart';

void main() {
  group('StatusChip', () {
    Widget wrap(Widget child) {
      return MaterialApp(
        home: Scaffold(body: Center(child: child)),
      );
    }

    testWidgets('renders open status', (tester) async {
      await tester.pumpWidget(wrap(const StatusChip(status: 'open')));
      expect(find.text('Offen'), findsOneWidget);
    });

    testWidgets('renders in_progress status', (tester) async {
      await tester.pumpWidget(wrap(const StatusChip(status: 'in_progress')));
      expect(find.text('In Arbeit'), findsOneWidget);
    });

    testWidgets('renders done status', (tester) async {
      await tester.pumpWidget(wrap(const StatusChip(status: 'done')));
      expect(find.text('Erledigt'), findsOneWidget);
    });

    testWidgets('renders custom label', (tester) async {
      await tester.pumpWidget(wrap(const StatusChip(status: 'open', label: 'Custom')));
      expect(find.text('Custom'), findsOneWidget);
    });
  });
}
