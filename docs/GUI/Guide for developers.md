# Coding GUI
![Logo](https://ericheilman.com/wp-content/uploads/2023/11/streamlit-logo-secondary-colormark-darktext.png?w=1568)

The gui has been created using `streamlit`, an open-source Python framework for data scientists and AI/ML engineers to deliver dynamic data apps with only a few lines of code. 

> Unfortunately, as of Streamlit version 1.10.0 and higher, Streamlit apps cannot be run from the root directory of Linux distributions. If you try to run a Streamlit app from the root directory, Streamlit will throw a FileNotFoundError: `[Errno 2] No such file or directory` error (see error [here](https://github.com/streamlit/streamlit/issues/5239)).




# Documentation

streamlit site:[(streamlit.io/](https://streamlit.io/)


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

