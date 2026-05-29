from textual.app import App


class TaggerApp(App):
    TITLE = "tagger"

    def on_mount(self) -> None:
        from screens.main_screen import MainScreen
        self.push_screen(MainScreen())
