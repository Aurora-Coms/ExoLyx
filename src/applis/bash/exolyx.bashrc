# Invite de commande ExoLyx (chargée par /etc/bash.bashrc pour les shells interactifs)
[[ $- != *i* ]] && return
_exo_vert='\[\e[38;2;168;212;121m\]'; _exo_doux='\[\e[38;2;151;168;147m\]'; _exo_rouge='\[\e[38;2;229;118;107m\]'; _exo_raz='\[\e[0m\]'
_exo_invite() {
  local code=$? fleche
  (( code == 0 )) && fleche="${_exo_vert}❯" || fleche="${_exo_rouge}❯"
  local branche=""
  if command -v git >/dev/null 2>&1; then
    branche=$(git symbolic-ref --short HEAD 2>/dev/null) && branche=" ${_exo_doux}(${branche})"
  fi
  local qui="${_exo_vert}\u"
  (( EUID == 0 )) && qui="${_exo_rouge}\u"
  PS1="${qui}${_exo_doux}@\h ${_exo_vert}\w${branche} ${fleche}${_exo_raz} "
}
PROMPT_COMMAND="_exo_invite${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
alias ls='ls --color=auto' grep='grep --color=auto' ll='ls -lh' la='ls -lha'
alias maj='exolyx-maj'
