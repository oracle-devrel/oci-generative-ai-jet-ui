# Change Log for oj-sample JET pack

## Version 9.0.0

* Upgrade to JET 15 base
* Terminal release of the sample component set - no further updates will be issued

## Version 8.0.0

* Upgrade to JET 14 base
* Deprecation of oj-sample-calendar, oj-sample-calendar-provider and oj-sample-calendar-event in favor of the supported component oj-sp-calendar
* Deprecation of oj-sample-organization-tree & oj-sample-organization-tree-item
* Removal of the deprecated oj-sample-pull-to-refresh which was replaced by oj-refresher in JET 5.1.0 

## Version 7.0.0

* Upgrade to JET 13 base
* Deprecation of oj-sample-drawer
* The contextMenu slot on oj-sample-checkbox-switch is now a no-op

## Version 6.0.1

* Address design time issue with oj-sample-timed-event in Visual Builder

## Version 6.0.0

* Upgrade to JET 12 base
* Bump in support range to ">=10.0.0 <13.0.0"

## Version 5.0.7

* Documentation and descriptive metadata clean up

## Version 5.0.6

* Bundling fixes

## Version 5.0.5

* Bug fixes in oj-sample-export-data and associated shared code update
* Updated implementations of oj-sample-copy-text and oj-sample-visualization-exporter for better Redwood compatibility

## Version 5.0.4

* Public JET 11 release

## Version 5.0.3

* Internal release version 

## Version 5.0.0

* Migration of the implementation of oj-sample-markdown-viewer to use the Marked library rather than Showdown.
* Various README formatting corrections
* Upgrade of overall supported JET version ranges to >= 9 <12
## Version 4.0.7

* Improve metadata to add implements and preferredContent throughout the pack

## Version 4.0.6

* Introduce packaged audits
## Version 4.0.5

* Introduce optimized bundles and CDN support
## Version 4.0.0

* Update for JET 10 compatibility
* JET minimum version increased to > 8.0.0
* Deprecation of oj-sample-pull-to-refresh in favor of oj-refresher
* Deprecation of oj-sample-highlight-text in favor of oj-highlight-text
## Version 3.2.4

* Update to downstream dependencies of calendar

## Version 3.2.3

* Minification packaging changes

## Version 3.2.2

* Documentation updates

## Version 3.2.1

* New icons for design time representation of the components
* Update chroming options on export components to be JET 8+ compatible

## Version 3.2.0

* Update across the pack for JET 9 support
* Addition of locale support to oj-sample-calendar
* Addition of keyboard selection support to oj-sample-metric
* Form embedding support for the Redwood Design system, ensuring that form components such as input-email display correctly
* Bug fix in design time of oj-sample-export-data to allow editing of selected columns through the property inspector

## Version 3.1.4

* Fix up of badly formed HTML in metric, show-when-ready and organization-tree-item
* Changes to minimum sizing for oj-sample-metric

## Version 3.1.3

* Bugfix for show-when-ready display of children

## Version 3.1.1

* Documentation improvements for pull-to-refresh

## Version 3.1.0

* oj-sample-input-url, oj-sample-input-email relocated from the oj-ext pack

## Version 3.0.0

* Expansion of JET support range to include JET 8
* Bug fixes to various components
* oj-sample-export-data, oj-sample-checkbox-switch, oj-sample-metric relocated from the oj-ext pack
* oj-sample-online-detector, oj-sample-orientation-detector and oj-sample-pull-to-refresh relocated from the oj-sample-mobile pack

## Version 2.3.1

* Visual Builder property inspector improvements for oj-sample-highlight-text
* Visual Builder design time improvements for oj-sample-tooltip

## Version 2.3.0

* Added new oj-sample-input-text-typeahead component for use on search-as-you-type style screens
* Fixed documentation error in highlight-text component where a hyphen was missing from one of the code samples
* Fixed problem with the property inspector for the tooltip component not showing correctly in Oracle Visual Builder

## Version 2.2.0

* Addition of the new oj-sample-highlight-text component
* Minor improvements to oj-sample-country-picker and oj-sample-tooltip

## Version 2.1.0

* Addition of the new oj-sample-tooltip component

## Version 2.0.3

* Expansion of JET-compatibility version ranges on components
* Bug fix for show-when-ready content not being interactive if state toggles more than once
* Bug fix for calendar to ensure that it refreshes if it is associated with a Data Provider that raises a change event

## Version 2.0.2

* Image updates for org tree

## Version 2.0.1

* Minor metadata cleanup

## Version 2.0.0

* Update to support JET 7.0.0

## Version 1.1.0

* Update baseline to JET 6.2.0 and replace use of deprecated JET APIs
* New oj-sample-organization-tree component added to the pack
* Race condition fix in show-when-ready when external state flag is toggled rapidly


## 1.0.1

* Bug fixes in oj-sample-drawer

## 1.0.0

* Initial release