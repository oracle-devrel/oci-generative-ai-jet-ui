package app

import tea "github.com/charmbracelet/bubbletea"

// Router manages view switching.
type Router struct {
	views  map[ViewID]View
	active ViewID
	width  int
	height int
}

func NewRouter(views map[ViewID]View, initial ViewID) *Router {
	r := &Router{
		views:  views,
		active: initial,
	}
	return r
}

func (r *Router) ActiveID() ViewID {
	return r.active
}

func (r *Router) ActiveView() View {
	if v, ok := r.views[r.active]; ok {
		return v
	}
	return nil
}

func (r *Router) SwitchTo(id ViewID) tea.Cmd {
	if _, ok := r.views[id]; !ok {
		return nil
	}
	r.active = id
	v := r.views[id]
	v.SetSize(r.width, r.height)
	return v.Init()
}

func (r *Router) SetSize(w, h int) {
	r.width = w
	r.height = h
	if v, ok := r.views[r.active]; ok {
		v.SetSize(w, h)
	}
}

func (r *Router) Update(msg tea.Msg) tea.Cmd {
	if v, ok := r.views[r.active]; ok {
		newView, cmd := v.Update(msg)
		r.views[r.active] = newView
		return cmd
	}
	return nil
}

func (r *Router) View() string {
	if v, ok := r.views[r.active]; ok {
		return v.View()
	}
	return ""
}

func (r *Router) RegisterView(v View) {
	r.views[v.ID()] = v
}
