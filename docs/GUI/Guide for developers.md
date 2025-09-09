# Coding GUI
![Logo](https://ericheilman.com/wp-content/uploads/2023/11/streamlit-logo-secondary-colormark-darktext.png?w=1568)

The gui has been created using ***Streamlit***, an open-source Python framework for data scientists and AI/ML engineers to deliver dynamic data writing them like plain Python scripts. Executing the command `streamlit run main.py`, a Streamlit server is started up. Whether users view your app across a local network or the internet, the Streamlit server runs on the one machine where the app was initialized with `streamlit run`. Apart from specific `streamlit` objects (like tables, buttons, input elements and so on), some words must be spent for the *Session State*. We define access to a Streamlit app in a browser tab as a **session**. For each browser tab that connects to the Streamlit server, a new session is created. Streamlit reruns your script from top to bottom every time you interact with your app. Each reruns takes place in a blank slate: no variables are shared between runs. ***Session State*** is a way to share variables between reruns, for each user session. In addition to the ability to store and persist state, Streamlit also exposes the ability to manipulate state using Callbacks.  The ***Session State*** API follows a field-based API, which is very similar to Python dictionaries:
>
```python
import streamlit as st

# Check if 'key' already exists in session_state
# If not, then initialize it
if 'key' not in st.session_state:
    st.session_state['key'] = 'value'

# Session State also supports the attribute based syntax
if 'key' not in st.session_state:
    st.session_state.key = 'value'

```
>
Read or chage this value can be done accessing to it both with `st.session_state.key` or `st.session_state["key"]`
> Streamlit throws an exception if an uninitialized variable is accessed (see the image below). In this case PVApp has a problem, so contact the developer to resolve it.
> ![streamlit-exception](/docs/GUI/img/state_uninitialized_exception.png)





## Documentation
streamlit site https://streamlit.io/
streamlit concept https://docs.streamlit.io/develop/concepts/architecture/session-state