import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    objectName: "previewWindow"
    width: 1280; height: 900
    minimumWidth: 1020; minimumHeight: 740
    visible: true
    title: preview.isDemo ? "政策周报 · 界面预览" : "政策周报"
    color: "#f3f6f2"
    palette.window: "#f3f6f2"
    palette.windowText: "#2a2b2a"
    palette.text: "#2a2b2a"
    font.family: Qt.platform.os === "osx" ? "PingFang SC" : "Microsoft YaHei UI"
    font.pixelSize: 13
    property int page: 0
    property bool reducedMotion: false
    property bool reducedTransparency: !preview.shaderSupported
    readonly property bool wallpaperReady: wallpaper.status === Image.Ready
    property real reveal: 0
    property real glyphReveal: 0
    property real logoTravel: 0
    property bool booting: true
    property string toastText: ""
    property bool toastShown: false
    property bool settingsReady: false
    property string desiredModel: ""
    readonly property int activeRecentDays: matchesRecentDays(7) ? 7 : matchesRecentDays(30) ? 30 : 0
    property var pageTitles: ["采集工作台", "站点管理", "历史报告", "偏好设置"]
    property var pageLabels: ["采集任务", "站点管理", "历史报告", "设置"]
    function replayIntro() {
        intro.stop(); reveal = 0; glyphReveal = 0; logoTravel = 0; booting = true
        if (reducedMotion) { reveal = 1; glyphReveal = 1; logoTravel = 1; booting = false }
        else intro.start()
    }
    function recentRange(days) {
        let end = new Date(); end.setDate(end.getDate() - 1)
        let start = new Date(end); start.setDate(start.getDate() - days + 1)
        return { start: startDate.format(start), end: endDate.format(end) }
    }
    function matchesRecentDays(days) {
        let range = recentRange(days)
        return startDate.value === range.start && endDate.value === range.end
    }
    function recentDays(days) {
        let range = recentRange(days)
        startDate.value = range.start; endDate.value = range.end
    }
    function finishIntro() {
        intro.stop(); reveal = 1; glyphReveal = 1; logoTravel = 1; booting = false
    }
    function currentOptions() {
        return {
            start_date: startDate.value, end_date: endDate.value,
            openai_base_url: apiUrl.text, openai_api_key: apiKey.text, openai_model: modelBox.currentText,
            use_llm: llmEnabled.checked, download_attachments: attachments.checked,
            browser_fallback: browserFallback.checked, strict_mode: strictMode.checked,
            verify_ssl: verifySsl.checked, allow_rule_fallback: ruleFallback.checked,
            sleep_seconds: interval.value / 10, reduced_motion: root.reducedMotion,
            reduced_transparency: root.reducedTransparency
        }
    }
    function queueSave() { if (settingsReady && !preview.isDemo) saveTimer.restart() }
    function selectSavedModel() {
        let model = root.desiredModel || modelBox.currentText
        let index = preview.modelOptions.indexOf(model)
        if (index < 0) index = preview.modelOptions.indexOf(root.desiredModel)
        modelBox.currentIndex = index >= 0 ? index : preview.modelOptions.length ? 0 : -1
    }
    Component.onCompleted: {
        recentDays(7)
        let s = preview.initialSettings
        if (s.start_date) startDate.value = s.start_date
        if (s.end_date) endDate.value = s.end_date
        apiUrl.text = s.openai_base_url || ""
        apiKey.text = s.openai_api_key || ""
        root.desiredModel = s.openai_model || ""
        llmEnabled.checked = s.use_llm === undefined ? true : s.use_llm
        attachments.checked = s.download_attachments === undefined ? false : s.download_attachments
        browserFallback.checked = s.browser_fallback === undefined ? true : s.browser_fallback
        strictMode.checked = s.strict_mode === undefined ? true : s.strict_mode
        verifySsl.checked = s.verify_ssl === undefined ? true : s.verify_ssl
        ruleFallback.checked = s.allow_rule_fallback || false
        interval.value = s.sleep_seconds === undefined ? 5 : Math.round(s.sleep_seconds * 10)
        root.reducedMotion = s.reduced_motion || false
        root.reducedTransparency = !preview.shaderSupported || s.reduced_transparency || false
        selectSavedModel()
        settingsReady = true
        replayIntro()
    }
    onReducedMotionChanged: queueSave()
    onReducedTransparencyChanged: queueSave()
    onPageChanged: { if (settingsReady && page === 2) preview.refreshReports() }
    onClosing: function(close) {
        if (settingsReady) preview.saveConfig(root.currentOptions())
        if (preview.running) { close.accepted = false; exitDialog.open() }
    }
    Timer { id: saveTimer; interval: 450; onTriggered: preview.saveConfig(root.currentOptions()) }
    Connections { target: sources; function onSelectionChanged() { root.queueSave() } }
    SequentialAnimation {
        id: intro
        NumberAnimation { target: root; property: "glyphReveal"; to: 1; duration: 1250; easing.type: Easing.Linear }
        ParallelAnimation {
            NumberAnimation { target: root; property: "logoTravel"; to: 1; duration: 550; easing.type: Easing.InOutCubic }
            NumberAnimation { target: root; property: "reveal"; to: 1; duration: 550; easing.type: Easing.OutCubic }
        }
        ScriptAction { script: root.booting = false }
    }
    Connections {
        target: preview
        function onToast(message) { root.toastText = message; root.toastShown = true; toastTimer.restart() }
        function onLogAdded() { if (logs.followTail) Qt.callLater(function() { logs.positionViewAtEnd() }) }
        function onModelsChanged() { Qt.callLater(function() { root.selectSavedModel(); root.queueSave() }) }
        function onCloseReady() { root.close() }
        function onApiBaseResolved(url) { apiUrl.text = url }
    }
    Timer { id: toastTimer; interval: 3500; onTriggered: root.toastShown = false }

    Item {
        id: scenery
        anchors.fill: parent
        clip: true
        Image {
            id: wallpaper
            objectName: "wallpaperImage"
            source: "assets/glacier-spiti.jpg"
            anchors.fill: parent
            fillMode: Image.PreserveAspectCrop
            smooth: true
        }
        Rectangle { anchors.fill: parent; color: "#40ffffff" }
    }
    ShaderEffectSource {
        id: backdropTexture
        sourceItem: scenery
        live: true
        hideSource: false
        visible: false
        textureSize: Qt.size(root.width, root.height)
    }
    Rectangle {
        y: 80; width: parent.width; height: parent.height - y
        color: "#f7faf8"
    }

    component SmallLabel: Text {
        color: "#616461"
        font.pixelSize: 12
    }
    component DatePreset: AppButton {
        id: preset
        required property int days
        readonly property bool selected: root.activeRecentDays === days
        text: "近 " + days + " 天"
        compact: true
        tone: "ghost"
        Accessible.checkable: true
        Accessible.checked: selected
        background: Rectangle {
            radius: 6
            color: preset.selected ? (preset.down ? "#d5e8de" : "#e5f0e9")
                 : preset.down ? "#dce9e1" : preset.hovered ? "#edf3ef" : "transparent"
            border.width: 1
            border.color: preset.selected ? "#4c8b6d" : preset.activeFocus ? "#6194c2" : "transparent"
            Behavior on color { ColorAnimation { duration: root.reducedMotion ? 0 : 120 } }
        }
        onClicked: root.recentDays(days)
    }
    component SectionTitle: RowLayout {
        property string title: ""
        property string marker: ""
        Layout.fillWidth: true
        spacing: 9
        Text { text: marker; color: "#7d807d"; font.pixelSize: 11; font.family: "Menlo" }
        Text { text: title; color: "#2d2e2d"; font.pixelSize: 13; font.weight: Font.DemiBold; Layout.fillWidth: true }
    }
    component Separator: Rectangle {
        Layout.fillWidth: true
        implicitHeight: 1
        color: "#e8efe8"
    }
    component SettingPair: RowLayout {
        property string label: ""
        property alias checked: switcher.checked
        Layout.fillWidth: true
        spacing: 8
        Text { text: label; color: "#484a48"; font.pixelSize: 12; Layout.fillWidth: true }
        Toggle { id: switcher; Accessible.name: label }
    }

    ColumnLayout {
        id: shell
        anchors.fill: parent
        spacing: 0
        opacity: root.reveal
        scale: 0.988 + 0.012 * root.reveal
        Item {
            Layout.fillWidth: true; Layout.preferredHeight: 80
            RowLayout {
                anchors { left: parent.left; leftMargin: 28; verticalCenter: parent.verticalCenter }
                spacing: 10
                GlassSurface {
                    width: 40; height: 42; radius: 12
                    texture: backdropTexture; scene: root.contentItem
                    whiteMix: 0.82
                    reducedTransparency: root.reducedTransparency
                    Icon { anchors.centerIn: parent; name: "file-text"; tint: "#24664a"; width: 23; height: 23 }
                }
                ColumnLayout {
                    spacing: 2
                    Text { text: "政策周报"; color: "#213e2e"; font.pixelSize: 17; font.weight: Font.DemiBold }
                    Text { text: "POLICY WEEKLY"; color: "#51665a"; font.pixelSize: 9 }
                }
            }
            GlassNavigation {
                id: mainNavigation; objectName: "mainNavigation"
                anchors.centerIn: parent
                currentIndex: root.page
                reducedMotion: root.reducedMotion
                reducedTransparency: root.reducedTransparency
                texture: backdropTexture; scene: root.contentItem
                onChosen: function(index) { root.page = index }
            }
            RowLayout {
                anchors { right: parent.right; rightMargin: 28; verticalCenter: parent.verticalCenter }
                spacing: 12
                Text { text: preview.isDemo ? "界面预览" : "本地工作台"; color: "#385442"; font.pixelSize: 11 }
                AppButton { iconName: "rotate-ccw"; tone: "ghost"; hint: "重播启动动画"; onClicked: root.replayIntro() }
            }
        }
        ColumnLayout {
            Layout.fillHeight: true; Layout.fillWidth: true
            spacing: 0
            Rectangle {
                Layout.fillWidth: true; height: 1; color: "#80ffffff"
            }
            Item {
                Layout.fillWidth: true; Layout.preferredHeight: 64
                ColumnLayout {
                    anchors { left: parent.left; leftMargin: 30; verticalCenter: parent.verticalCenter }
                    spacing: 6
                    Text { text: root.pageTitles[root.page]; color: "#252625"; font.pixelSize: 23; font.weight: Font.DemiBold }
                }
                RowLayout {
                    anchors { right: parent.right; rightMargin: 30; verticalCenter: parent.verticalCenter }
                    spacing: 12
                    AppButton {
                        objectName: "openLastPdf"; visible: !preview.isDemo && preview.lastPdf.length > 0
                        text: "打开本次 PDF"; iconName: "external-link"
                        onClicked: preview.openFile(preview.lastPdf)
                    }
                    AppButton {
                        objectName: "startButton"
                        visible: root.page === 0
                        text: preview.stopping ? "正在停止" : preview.running ? "停止" : preview.isDemo ? "开始演示" : "开始生成"
                        iconName: preview.running ? "square" : "play"
                        tone: preview.running ? "danger" : "primary"
                        enabled: !preview.stopping && !preview.modelsLoading && (preview.running || sources.selectedCount > 0)
                        onClicked: preview.running ? preview.stop() : preview.start(startDate.value, endDate.value, root.currentOptions())
                    }
                }
            }
            Separator {}
            Item {
                id: pages
                Layout.fillWidth: true; Layout.fillHeight: true

                ColumnLayout {
                    id: collectionPage
                    anchors.fill: parent
                    opacity: root.page === 0 ? 1 : 0
                    visible: opacity > 0
                    enabled: root.page === 0
                    Behavior on opacity { NumberAnimation { duration: root.reducedMotion ? 0 : 170 } }
                    spacing: 0
                    RowLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        spacing: 0
                        ScrollView {
                            id: configScroll
                            objectName: "configScroll"
                            Layout.fillHeight: true; Layout.fillWidth: true
                            contentWidth: availableWidth
                            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                            ScrollBar.vertical.policy: ScrollBar.AsNeeded
                            clip: true
                            ColumnLayout {
                                width: configScroll.availableWidth - 60
                                x: 30; y: 18
                                spacing: 8
                                enabled: !preview.running
                                opacity: enabled ? 1 : 0.65
                                SectionTitle {
                                    title: "统计周期"; marker: "01"
                                    DatePreset { objectName: "recent7Days"; days: 7 }
                                    DatePreset { objectName: "recent30Days"; days: 30 }
                                }
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 12
                                    DateField { onValueChanged: root.queueSave(); id: startDate; objectName: "startDate"; Layout.fillWidth: true; glassTexture: backdropTexture; glassScene: root.contentItem; reducedTransparency: root.reducedTransparency }
                                    Text { text: "至"; color: "#7b7f7b"; font.pixelSize: 12 }
                                    DateField { onValueChanged: root.queueSave(); id: endDate; objectName: "endDate"; Layout.fillWidth: true; glassTexture: backdropTexture; glassScene: root.contentItem; reducedTransparency: root.reducedTransparency }
                                }
                                Separator { Layout.topMargin: 8; Layout.bottomMargin: 7 }
                                SectionTitle {
                                    title: "大模型配置"; marker: "02"
                                    SmallLabel { text: llmEnabled.checked ? "已启用" : "已关闭"; color: "#6b6e6b"; font.pixelSize: 11 }
                                    Toggle { id: llmEnabled; checked: true; onCheckedChanged: root.queueSave(); Accessible.name: "启用大模型" }
                                }
                                GridLayout {
                                    Layout.fillWidth: true; columns: 2; columnSpacing: 14; rowSpacing: 7
                                    uniformCellWidths: true
                                    enabled: llmEnabled.checked && !preview.modelsLoading
                                    SmallLabel { text: "接口地址" }
                                    SmallLabel { text: "API Key" }
                                    Field { id: apiUrl; objectName: "apiUrl"; Layout.fillWidth: true; placeholderText: "https://api.example.com/v1"; onTextChanged: root.queueSave() }
                                    Item {
                                        Layout.fillWidth: true; Layout.preferredHeight: 38
                                        Field {
                                            id: apiKey; objectName: "apiKey"; anchors.fill: parent
                                            readonly property bool keyHidden: echoMode === TextInput.Password
                                            placeholderText: "输入 API Key"; echoMode: revealKey.checked ? TextInput.Normal : TextInput.Password
                                            passwordCharacter: "●"; rightPadding: 37
                                            onTextChanged: root.queueSave()
                                        }
                                        AppButton {
                                            id: revealKey; objectName: "revealKey"
                                            anchors.right: parent.right; anchors.rightMargin: 3; anchors.verticalCenter: parent.verticalCenter
                                            width: 31; height: 30; compact: true; tone: "ghost"; checkable: true
                                            iconName: checked ? "eye-off" : "eye"; hint: checked ? "隐藏密钥" : "显示密钥"
                                        }
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 10
                                    ComboBox {
                                        id: modelBox; objectName: "modelBox"
                                        Layout.fillWidth: true; implicitHeight: 36
                                        model: preview.modelOptions
                                        enabled: llmEnabled.checked
                                        leftPadding: 12; rightPadding: 30
                                        contentItem: Text { text: modelBox.displayText || "未获取模型"; verticalAlignment: Text.AlignVCenter; color: modelBox.currentIndex >= 0 ? "#313231" : "#727572"; font.pixelSize: 13; elide: Text.ElideRight }
                                        background: Rectangle { radius: 6; color: "#ebf2eb"; border.width: 1; border.color: modelBox.activeFocus ? "#4f8f6b" : "#e6ede6" }
                                        indicator: Icon { name: "chevrons-up-down"; x: modelBox.width - 25; y: 11; width: 14; height: 14 }
                                        delegate: ItemDelegate {
                                            required property string modelData
                                            required property int index
                                            width: modelBox.width - 8; height: 34
                                            highlighted: modelBox.highlightedIndex === index
                                            background: Rectangle { radius: 4; color: parent.hovered || parent.highlighted ? "#e4ebe4" : "transparent" }
                                            contentItem: Text { text: modelData; color: "#303230"; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                                            onClicked: { modelBox.currentIndex = index; root.desiredModel = modelData; modelBox.popup.close(); root.queueSave() }
                                        }
                                        onActivated: { root.desiredModel = currentText; root.queueSave() }
                                        popup: Popup {
                                            y: modelBox.height + 5; width: modelBox.width; padding: 4
                                            implicitHeight: Math.min(modelList.contentHeight, 280) + 8
                                            background: GlassSurface { texture: backdropTexture; scene: root.contentItem; radius: 10; frost: 8; whiteMix: 0.97; reducedTransparency: root.reducedTransparency }
                                            contentItem: ListView {
                                                id: modelList; objectName: "modelList"
                                                clip: true; implicitHeight: contentHeight
                                                model: modelBox.popup.visible ? modelBox.delegateModel : null
                                                currentIndex: modelBox.highlightedIndex
                                                ScrollBar.vertical: ScrollBar { width: 7 }
                                            }
                                        }
                                    }
                                    AppButton {
                                        objectName: "fetchModels"; text: preview.modelsLoading ? "获取中…" : "获取模型"; iconName: "refresh-cw"; enabled: llmEnabled.checked && !preview.modelsLoading
                                        onClicked: { preview.saveConfig(root.currentOptions()); preview.fetchModels(apiUrl.text, apiKey.text, verifySsl.checked) }
                                    }
                                }
                                Separator { Layout.topMargin: 8; Layout.bottomMargin: 7 }
                                SectionTitle {
                                    title: "运行设置"; marker: "03"
                                    SmallLabel { text: "请求间隔"; font.pixelSize: 11 }
                                    Rectangle {
                                        id: interval; objectName: "requestInterval"
                                        property int value: 5
                                        onValueChanged: root.queueSave()
                                        Layout.preferredWidth: 98; Layout.preferredHeight: 28
                                        radius: 4; color: "#ebf2eb"; border.width: 1; border.color: "#e5ece5"
                                        activeFocusOnTab: true
                                        Accessible.role: Accessible.SpinBox
                                        Accessible.name: "请求间隔 " + (value / 10).toFixed(1) + " 秒"
                                        Keys.onUpPressed: value = Math.min(600, value + 1)
                                        Keys.onDownPressed: value = Math.max(0, value - 1)
                                        AppButton { x: 1; y: 1; width: 25; height: 26; compact: true; tone: "ghost"; iconName: "minus"; hint: "减少请求间隔"; onClicked: interval.value = Math.max(0, interval.value - 1) }
                                        Text { anchors.centerIn: parent; text: (interval.value / 10).toFixed(1) + " s"; color: "#464846"; font.pixelSize: 11 }
                                        AppButton { anchors.right: parent.right; anchors.rightMargin: 1; y: 1; width: 25; height: 26; compact: true; tone: "ghost"; iconName: "plus"; hint: "增加请求间隔"; onClicked: interval.value = Math.min(600, interval.value + 1) }
                                    }
                                }
                                GridLayout {
                                    Layout.fillWidth: true; columns: 2; columnSpacing: 28; rowSpacing: 4
                                    SettingPair { id: attachments; objectName: "attachments"; label: "下载附件"; checked: false; onCheckedChanged: root.queueSave() }
                                    SettingPair { id: verifySsl; objectName: "verifySsl"; label: "校验 SSL"; checked: true; onCheckedChanged: root.queueSave() }
                                    SettingPair { id: browserFallback; objectName: "browserFallback"; label: "浏览器兜底"; checked: true; onCheckedChanged: root.queueSave() }
                                    SettingPair { id: strictMode; objectName: "strictMode"; label: "严格筛选"; checked: true; onCheckedChanged: root.queueSave() }
                                }
                                CheckControl { id: ruleFallback; objectName: "ruleFallback"; text: "模型不可用时使用规则兜底"; checked: false; onCheckedChanged: root.queueSave() }
                                Separator { Layout.topMargin: 6; Layout.bottomMargin: 7 }
                                SectionTitle {
                                    title: "采集站点"; marker: "04"
                                    Text { text: "不限栏目 · 不限详情"; color: "#747774"; font.pixelSize: 11 }
                                }
                                SourcePicker { id: sitePicker; objectName: "sitePicker"; Layout.fillWidth: true; glassTexture: backdropTexture; glassScene: root.contentItem; reducedTransparency: root.reducedTransparency }
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 7
                                    Icon { name: "folder-open"; width: 14; height: 14; tint: "#7a7d7a" }
                                    Text { text: preview.outputPath; font.pixelSize: 11; color: "#6e726e"; elide: Text.ElideMiddle; Layout.fillWidth: true }
                                    AppButton { text: "更改"; tone: "ghost"; compact: true; hint: "选择输出目录"; onClicked: preview.chooseOutput() }
                                }
                                Item { Layout.preferredHeight: 22 }
                            }
                        }
                        Rectangle { Layout.fillHeight: true; width: 1; color: "#e8efe8" }
                        Rectangle {
                            Layout.preferredWidth: root.width < 1130 ? 264 : 302
                            Layout.fillHeight: true
                            color: "#f0f4ef"
                            ScrollView {
                                id: monitorScroll
                                anchors.fill: parent
                                contentWidth: availableWidth
                                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                clip: true
                                ColumnLayout {
                                    width: monitorScroll.availableWidth - 44
                                    x: 22; y: 26; spacing: 18
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Icon { name: "activity"; width: 16; height: 16; tint: "#267451" }
                                        Text { text: "任务概览"; color: "#3b3d3b"; font.pixelSize: 13; font.weight: Font.DemiBold; Layout.fillWidth: true }
                                        Rectangle { width: 6; height: 6; radius: 3; color: preview.running ? "#267451" : "#7d817d"; opacity: pulse.running ? 0.6 : 1
                                            SequentialAnimation on opacity { id: pulse; running: preview.running && !root.reducedMotion; loops: Animation.Infinite; NumberAnimation { to: 0.3; duration: 700 } NumberAnimation { to: 1; duration: 700 } }
                                        }
                                    }
                                    ColumnLayout {
                                        spacing: 7; Layout.fillWidth: true
                                        Text { text: preview.state; color: "#262726"; font.pixelSize: 22; font.weight: Font.Medium; Layout.fillWidth: true; wrapMode: Text.Wrap }
                                        Text { text: preview.isDemo ? "离线演示 / 无网络请求" : "真实任务 / 本地报告"; font.pixelSize: 11; color: "#6f736f" }
                                    }
                                    Separator {}
                                    GridLayout {
                                        Layout.fillWidth: true; columns: 2; columnSpacing: 22; rowSpacing: 8
                                        SmallLabel { text: "已处理站点" }
                                        SmallLabel { text: "耗时" }
                                        Row {
                                            spacing: 4
                                            Text { text: preview.done; font.pixelSize: 27; color: "#292a29" }
                                            Text { text: "/ " + (preview.running || preview.done > 0 ? preview.total : sources.selectedCount); font.pixelSize: 12; color: "#6f726f"; anchors.bottom: parent.bottom; anchors.bottomMargin: 4 }
                                        }
                                        Text { text: preview.elapsed; font.pixelSize: 24; color: "#313331" }
                                        SmallLabel { text: preview.isDemo ? "处理页面（演示）" : "处理页面"; font.pixelSize: 11; Layout.topMargin: 10 }
                                        SmallLabel { text: preview.isDemo ? "收录信息（演示）" : "收录信息"; font.pixelSize: 11; Layout.topMargin: 10 }
                                        Text { text: preview.pages; font.pixelSize: 23; color: "#3c3e3c" }
                                        Text { text: preview.hits; font.pixelSize: 23; color: "#267451" }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true; height: 3; color: "#e5ece5"; radius: 1.5
                                        Rectangle {
                                            height: 3; radius: 1.5; color: "#267451"
                                            width: parent.width * (preview.total ? preview.done / preview.total : 0)
                                            Behavior on width { NumberAnimation { duration: root.reducedMotion ? 0 : 250 } }
                                        }
                                    }
                                    Text {
                                        text: preview.stageSummary; color: "#646764"; font.pixelSize: 11
                                        Layout.fillWidth: true; wrapMode: Text.Wrap
                                    }
                                    ColumnLayout {
                                        spacing: 9; Layout.fillWidth: true
                                        SmallLabel { text: preview.running ? "正在处理" : preview.done > 0 ? "最近任务" : "当前站点"; font.pixelSize: 11 }
                                        Text { text: preview.currentSite; color: "#3d3f3d"; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                        Text { text: preview.activeSources; visible: text.length > 0; color: "#646764"; font.pixelSize: 11; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                        Text { text: preview.currentColumn; visible: text.length > 0; color: "#646764"; font.pixelSize: 11; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true; maximumLineCount: 2; elide: Text.ElideRight }
                                        RowLayout {
                                            spacing: 6
                                            Icon { name: preview.running ? "refresh-cw" : "circle-check"; width: 13; height: 13; tint: "#6c706c" }
                                            Text { text: preview.phase; color: "#646764"; font.pixelSize: 11 }
                                        }
                                    }
                                    Separator { Layout.topMargin: 2 }
                                    ColumnLayout {
                                        Layout.fillWidth: true; spacing: 14
                                        Repeater {
                                            model: ["栏目与列表", "详情提取", "分类与汇总", "PDF 报告"]
                                            RowLayout {
                                                required property string modelData; required property int index
                                                Layout.fillWidth: true; spacing: 11
                                                Rectangle {
                                                    width: 22; height: 22; radius: 11; color: "#e9f0e9"; border.width: 1; border.color: "#888c88"
                                                    Text { anchors.centerIn: parent; text: (index + 1).toString().padStart(2, "0"); font.pixelSize: 9; color: "#626562" }
                                                }
                                                Text { text: modelData; font.pixelSize: 12; color: "#5f625f"; Layout.fillWidth: true }
                                                Icon { name: "chevron-right"; width: 12; height: 12; tint: "#848884" }
                                            }
                                        }
                                    }
                                    Item { Layout.preferredHeight: 12 }
                                }
                            }
                        }
                    }
                    Separator {}
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: logToggle.checked ? (root.height < 810 ? 135 : 150) : 42
                        color: "#eaf0ea"
                        Behavior on Layout.preferredHeight { NumberAnimation { duration: root.reducedMotion ? 0 : 160; easing.type: Easing.OutCubic } }
                        ColumnLayout {
                            anchors.fill: parent; spacing: 0
                            RowLayout {
                                Layout.fillWidth: true; Layout.preferredHeight: 42; Layout.leftMargin: 26; Layout.rightMargin: 22
                                Icon { name: "terminal"; width: 15; height: 15; tint: "#636663" }
                                Text { text: "运行日志"; color: "#454745"; font.pixelSize: 12 }
                                Rectangle {
                                    implicitWidth: 43; implicitHeight: 18; radius: 3; color: "#e9f0e9"
                                    Text { anchors.centerIn: parent; text: preview.isDemo ? "DEMO" : "LIVE"; font.pixelSize: 8; color: "#616461" }
                                }
                                Item { Layout.fillWidth: true }
                                Field {
                                    id: logSearch; objectName: "logSearch"
                                    visible: logToggle.checked
                                    Layout.preferredWidth: 160; implicitHeight: 26; font.pixelSize: 11
                                    placeholderText: "筛选日志"; onTextChanged: logModel.query = text
                                }
                                AppButton { iconName: "x"; compact: true; tone: "ghost"; hint: "清空日志"; onClicked: preview.clearLogs() }
                                AppButton { id: logToggle; iconName: "chevron-down"; compact: true; tone: "ghost"; hint: checked ? "收起日志" : "展开日志"; checkable: true; checked: true; rotation: checked ? 0 : 180 }
                            }
                            ListView {
                                id: logs; objectName: "logList"
                                property bool followTail: true
                                Layout.fillWidth: true; Layout.fillHeight: true; Layout.leftMargin: 28; Layout.rightMargin: 18; Layout.bottomMargin: 12
                                visible: logToggle.checked
                                clip: true; model: logModel; spacing: 2
                                boundsBehavior: Flickable.StopAtBounds
                                ScrollBar.vertical: ScrollBar {
                                    id: logScrollbar
                                    width: 7
                                    onPressedChanged: { if (!pressed) logs.followTail = logs.atYEnd }
                                }
                                onMovementStarted: followTail = false
                                onMovementEnded: followTail = atYEnd
                                WheelHandler {
                                    target: null; blocking: false
                                    onWheel: function(event) {
                                        if (event.angleDelta.y > 0 || event.pixelDelta.y > 0) logs.followTail = false
                                        else Qt.callLater(function() { if (logs.atYEnd) logs.followTail = true })
                                    }
                                }
                                delegate: Item {
                                    required property string logTime
                                    required property string level
                                    required property string message
                                    width: logs.width - 12
                                    height: Math.max(21, logMessage.implicitHeight + 4)
                                    RowLayout {
                                        anchors { left: parent.left; right: parent.right; top: parent.top }
                                        spacing: 14
                                        Text { text: logTime; font.family: "Menlo"; font.pixelSize: 10; color: "#7e827e"; Layout.alignment: Qt.AlignTop; Layout.topMargin: 3 }
                                        Text { text: level; font.pixelSize: 9; color: level === "READY" || level === "DONE" ? "#545754" : level === "STOP" ? "#9c6d2a" : "#6a6d6a"; Layout.preferredWidth: 36; Layout.alignment: Qt.AlignTop; Layout.topMargin: 4 }
                                        Text { id: logMessage; text: message; font.pixelSize: 11; color: "#585b58"; Layout.fillWidth: true; wrapMode: Text.Wrap; lineHeight: 1.35 }
                                    }
                                }
                                AppButton {
                                    anchors.right: parent.right; anchors.rightMargin: 14; anchors.bottom: parent.bottom
                                    iconName: "arrow-down"; compact: true; hint: "回到最新日志"; visible: !logs.followTail
                                    onClicked: { logs.followTail = true; logs.positionViewAtEnd() }
                                }
                            }
                        }
                    }
                }

                ColumnLayout {
                    id: sitesPage
                    anchors { fill: parent; margins: 30 }
                    opacity: root.page === 1 ? 1 : 0
                    visible: opacity > 0
                    enabled: root.page === 1
                    Behavior on opacity { NumberAnimation { duration: root.reducedMotion ? 0 : 170 } }
                    spacing: 18
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            spacing: 6
                            Text { text: sources.total + " 个采集站点"; color: "#2c2e2c"; font.pixelSize: 17; font.weight: Font.DemiBold }
                            SmallLabel { text: "5 个地区 · 6 类部门" }
                        }
                        Item { Layout.fillWidth: true }
                        Field { id: manageSearch; objectName: "manageSearch"; Layout.preferredWidth: 235; placeholderText: "搜索站点或地区"; onTextChanged: manageFilter.query = text }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        CheckControl { text: "全部站点"; checked: sources.selectedCount === sources.total; partial: sources.selectedCount > 0 && sources.selectedCount < sources.total; enabled: !preview.running; onClicked: sources.selectAll(sources.selectedCount !== sources.total) }
                        Item { Layout.fillWidth: true }
                        SmallLabel { text: "已选择 " + sources.selectedCount + " / " + sources.total }
                    }
                    Separator {}
                    RowLayout {
                        Layout.fillWidth: true; Layout.leftMargin: 42; Layout.rightMargin: 44; spacing: 16
                        SmallLabel { text: "站点名称"; Layout.fillWidth: true }
                        SmallLabel { text: "地区"; Layout.preferredWidth: 60 }
                        SmallLabel { text: "配置栏目"; Layout.preferredWidth: 70 }
                        SmallLabel { text: "配置状态"; Layout.preferredWidth: 70 }
                    }
                    ListView {
                        id: manageList; objectName: "manageList"
                        Layout.fillWidth: true; Layout.fillHeight: true
                        model: manageFilter; clip: true; spacing: 0
                        ScrollBar.vertical: ScrollBar { width: 8 }
                        delegate: Item {
                            required property int siteId; required property string siteName; required property string region
                            required property int channels; required property bool selected; required property string siteUrl
                            width: manageList.width; height: 58
                            Rectangle { anchors.fill: parent; color: manageHover.hovered ? "#ebf2eb" : "transparent"; radius: 5 }
                            HoverHandler { id: manageHover }
                            RowLayout {
                                anchors.fill: parent; spacing: 16
                                CheckControl { Layout.preferredWidth: 24; Layout.leftMargin: 8; checked: selected; enabled: !preview.running; onClicked: sources.toggle(siteId) }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 4
                                    Text { text: siteName; color: "#333533"; font.pixelSize: 13; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Text { text: siteUrl; color: "#7a7e7a"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                }
                                SmallLabel { text: region; Layout.preferredWidth: 60 }
                                SmallLabel { text: channels; Layout.preferredWidth: 70 }
                                RowLayout { Layout.preferredWidth: 70; spacing: 6; Rectangle { width: 4; height: 4; radius: 2; color: "#43805c" } SmallLabel { text: "已配置"; color: "#43805c" } }
                                AppButton { iconName: "arrow-up-right"; tone: "ghost"; compact: true; hint: "在浏览器打开网站"; onClicked: preview.openSite(siteUrl) }
                            }
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#e9f0e9" }
                        }
                        Text { anchors.centerIn: parent; visible: manageList.count === 0; text: "没有匹配的站点"; color: "#696c69"; font.pixelSize: 14 }
                    }
                }

                ColumnLayout {
                    anchors { fill: parent; margins: 30 }
                    opacity: root.page === 2 ? 1 : 0
                    visible: opacity > 0
                    enabled: root.page === 2
                    Behavior on opacity { NumberAnimation { duration: root.reducedMotion ? 0 : 170 } }
                    spacing: 20
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "本地 PDF 报告"; color: "#2e302e"; font.pixelSize: 16; font.weight: Font.DemiBold; Layout.fillWidth: true }
                        AppButton { iconName: "refresh-cw"; hint: "刷新报告列表"; tone: "ghost"; onClicked: preview.refreshReports() }
                        AppButton { text: "打开输出目录"; iconName: "folder-open"; onClicked: preview.openFile(preview.outputPath) }
                    }
                    Separator {}
                    ListView {
                        id: reportList
                        Layout.fillWidth: true; Layout.fillHeight: true
                        model: reportModel; spacing: 12; clip: true
                        ScrollBar.vertical: ScrollBar { width: 8 }
                        delegate: Rectangle {
                            required property string reportName; required property string reportPath
                            required property string reportDate; required property string reportSize
                            width: reportList.width; height: 78; radius: 6; color: "#ebf2eb"; border.width: 1; border.color: "#e6ede6"
                            RowLayout {
                                anchors { fill: parent; leftMargin: 20; rightMargin: 16 }
                                spacing: 18
                                Icon { name: "file-text"; tint: "#468363"; width: 26; height: 26 }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 7
                                    Text { text: reportName; color: "#2d2f2d"; font.pixelSize: 14; Layout.fillWidth: true; elide: Text.ElideRight }
                                    SmallLabel { text: reportDate + "  ·  " + reportSize; font.pixelSize: 11 }
                                }
                                AppButton { iconName: "external-link"; text: "打开 PDF"; onClicked: preview.openFile(reportPath) }
                            }
                        }
                        ColumnLayout {
                            anchors.centerIn: parent; spacing: 15; visible: reportList.count === 0
                            Icon { name: "file-text"; width: 42; height: 42; tint: "#818581"; Layout.alignment: Qt.AlignHCenter }
                            Text { text: "暂无本地报告"; font.pixelSize: 16; color: "#454845"; Layout.alignment: Qt.AlignHCenter }
                        }
                    }
                }

                ColumnLayout {
                    anchors { fill: parent; margins: 30 }
                    opacity: root.page === 3 ? 1 : 0
                    visible: opacity > 0
                    enabled: root.page === 3
                    Behavior on opacity { NumberAnimation { duration: root.reducedMotion ? 0 : 170 } }
                    spacing: 22
                    Text { text: "外观与交互"; color: "#2c2e2c"; font.pixelSize: 16; font.weight: Font.DemiBold }
                    Separator {}
                    RowLayout {
                        Layout.fillWidth: true; Layout.preferredHeight: 46
                        SmallLabel { text: "外观"; Layout.fillWidth: true; font.pixelSize: 13 }
                        Text { text: "浅色玻璃"; color: "#393b39"; font.pixelSize: 13 }
                        Rectangle { width: 22; height: 22; radius: 5; color: "#eaf1ea"; border.width: 1; border.color: "#7b7f7b" }
                    }
                    Separator {}
                    RowLayout {
                        Layout.fillWidth: true; Layout.preferredHeight: 46
                        SmallLabel { text: "减少动态效果"; Layout.fillWidth: true; font.pixelSize: 13 }
                        Toggle { objectName: "reducedMotion"; checked: root.reducedMotion; onClicked: root.reducedMotion = checked; Accessible.name: "减少动态效果" }
                    }
                    Separator {}
                    RowLayout {
                        Layout.fillWidth: true; Layout.preferredHeight: 46
                        SmallLabel { text: "启动动画"; Layout.fillWidth: true; font.pixelSize: 13 }
                        AppButton { text: "重新播放"; iconName: "rotate-ccw"; onClicked: root.replayIntro() }
                    }
                    Separator {}
                    RowLayout {
                        Layout.fillWidth: true; Layout.preferredHeight: 46
                        SmallLabel { text: "运行模式"; Layout.fillWidth: true; font.pixelSize: 13 }
                        Text { text: preview.isDemo ? "离线界面预览" : "真实采集"; color: "#3c7755"; font.pixelSize: 13 }
                    }
                    Separator {}
                    RowLayout {
                        Layout.fillWidth: true; Layout.preferredHeight: 46
                        SmallLabel { text: "减少透明效果"; Layout.fillWidth: true; font.pixelSize: 13 }
                        Toggle { objectName: "reducedTransparency"; checked: root.reducedTransparency; onClicked: root.reducedTransparency = checked; Accessible.name: "减少透明效果" }
                    }
                    Item { Layout.fillHeight: true }
                    Text { text: preview.isDemo ? "Policy Weekly / Design Preview 02" : "Policy Weekly / Desktop"; color: "#7e827e"; font.pixelSize: 11 }
                }
            }
            Separator {}
            RowLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 30; Layout.leftMargin: 28; Layout.rightMargin: 26
                spacing: 7
                Icon { name: "shield-check"; width: 12; height: 12; tint: "#747874" }
                Text { text: preview.isDemo ? "离线预览" : "本地运行"; color: "#6f726f"; font.pixelSize: 10 }
                Rectangle { width: 1; height: 9; color: "#e3eae3"; Layout.leftMargin: 5; Layout.rightMargin: 5 }
                Text { text: sources.selectedCount + " 个站点已选"; color: "#7b7f7b"; font.pixelSize: 10 }
                Item { Layout.fillWidth: true }
                Text { text: "PDF"; color: "#6b6e6b"; font.pixelSize: 10 }
                Text { text: "·"; color: "#818581"; font.pixelSize: 11 }
                Text { text: "本地输出"; color: "#7b7f7b"; font.pixelSize: 10 }
            }
        }
    }

    Dialog {
        id: exitDialog; objectName: "exitDialog"
        anchors.centerIn: parent; width: 360; modal: true
        title: "任务正在运行"
        standardButtons: Dialog.Yes | Dialog.No
        contentItem: Text { text: "退出会停止当前采集任务。确定退出吗？"; color: "#344b3b"; font.pixelSize: 13; wrapMode: Text.Wrap }
        onAccepted: { preview.saveConfig(root.currentOptions()); preview.requestExit() }
    }

    StartupScene {
        id: startup; objectName: "startupScene"
        anchors.fill: parent
        visible: root.booting; z: 10
        progress: root.glyphReveal
        departure: root.logoTravel
        reducedMotion: root.reducedMotion
        onSkipRequested: root.finishIntro()
    }
    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom; anchors.bottomMargin: 48
        width: Math.min(toastLabel.implicitWidth + 40, root.width - 80)
        height: 44; radius: 7
        color: "#e7eee7"; border.width: 1; border.color: "#828682"
        opacity: root.toastShown ? 1 : 0
        visible: opacity > 0
        z: 20
        Behavior on opacity { NumberAnimation { duration: 160 } }
        Text { id: toastLabel; anchors.centerIn: parent; text: root.toastText; font.pixelSize: 12; color: "#313331"; width: Math.min(implicitWidth, parent.width - 30); elide: Text.ElideRight }
    }
}
