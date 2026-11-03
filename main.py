"""Ponto de entrada do Renomeador de Declaracoes."""
import multiprocessing

from cartorio.instancia import InstanciaUnica


def main():
    instancia = InstanciaUnica()
    if not instancia.adquirir():
        # Ja existe uma janela aberta: pede para ela aparecer e encerra.
        if instancia.avisar_existente():
            return
        # Porta ocupada por outro programa: segue sem a protecao.

    from cartorio.ui.app import App
    app = App()
    instancia.ouvir(lambda: app.after(0, app.trazer_para_frente))
    try:
        app.mainloop()
    finally:
        instancia.liberar()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
