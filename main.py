"""Ponto de entrada do Renomeador de Declaracoes."""
import multiprocessing

from cartorio.ui.app import App


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = App()
    app.mainloop()
