> ‼️ Future update:
> - Notifiche con streamlit-custom-notification-box (https://github.com/Socvest/streamlit-custom-notification-box): 
>```python
>  styles = {'material-icons':{'color': 'red'},
>                      'text-icon-link-close-container': {'box-shadow': '#3896de 0px 4px'},
>                      'notification-text': {'':''},
>                      'close-button':{'':''},
>                      'link':{'':''}}
>
>            custom_notification_box(icon='info', textDisplay=f"Simulation for {plant["name"]} in site {site["name"]} done", externalLink='more info', url='#', styles=styles, key="foo")
>           