/*
 * Services tiers + mesure d'audience — modèle opt-out Paper34.
 *
 * - Google Maps : actif par défaut, mais l'iframe n'est créée qu'à l'approche
 *   du bloc (IntersectionObserver) → rien de chargé chez Google tant que la
 *   carte n'est pas à l'écran. Refus mémorisé : localStorage
 *   « espace-ongles-off-maps » ; un encadré de repli garde l'adresse et les
 *   itinéraires, avec un bouton de réactivation.
 * - Panneau « Préférences de confidentialité » ouvert à la demande depuis le
 *   pied de page (lien [data-prefs]).
 * - Vercel Web Analytics (sans cookie, exempté de consentement) + événements :
 *   tel, reservation, itineraire, instagram, bon-cadeau.
 */
(function () {
  var CLE_MAPS = 'espace-ongles-off-maps';
  var URL_CARTE = 'https://www.google.com/maps?q=Espace+Ongles,+9+Place+Bonnet,+34120+P%C3%A9zenas&hl=fr&z=17&output=embed';

  function lire(cle) { try { return localStorage.getItem(cle) === '1'; } catch (e) { return false; } }
  function ecrire(cle, coupe) {
    try { coupe ? localStorage.setItem(cle, '1') : localStorage.removeItem(cle); } catch (e) {}
  }

  /* ─── Carte Google Maps ─── */
  function monterCarte(bloc) {
    if (bloc.querySelector('iframe')) return;
    var f = document.createElement('iframe');
    f.src = URL_CARTE;
    f.title = 'Espace Ongles, 9 Place Bonnet à Pézenas, sur Google Maps';
    f.loading = 'lazy';
    f.referrerPolicy = 'no-referrer-when-downgrade';
    f.setAttribute('allowfullscreen', '');
    bloc.appendChild(f);
  }

  function repli(bloc) {
    bloc.classList.add('carte-coupee');
    bloc.innerHTML =
      '<div class="carte-repli">' +
      '<p class="carte-repli-titre">Carte désactivée</p>' +
      '<p>Espace Ongles<br>9 Place Bonnet, 34120 Pézenas</p>' +
      '<p class="carte-repli-liens">' +
      '<a href="https://www.google.com/maps/dir/?api=1&destination=Espace+Ongles+9+Place+Bonnet+34120+P%C3%A9zenas" target="_blank" rel="noopener" data-track="itineraire">Itinéraire Google Maps</a>' +
      '<a href="https://maps.apple.com/?daddr=9+Place+Bonnet,+34120+P%C3%A9zenas" target="_blank" rel="noopener" data-track="itineraire">Plans (Apple)</a>' +
      '</p>' +
      '<button type="button" class="carte-repli-btn">Afficher la carte</button>' +
      '</div>';
    bloc.querySelector('button').addEventListener('click', function () {
      ecrire(CLE_MAPS, false);
      location.reload();
    });
  }

  document.querySelectorAll('[data-carte]').forEach(function (bloc) {
    if (lire(CLE_MAPS)) return repli(bloc);
    if (!('IntersectionObserver' in window)) return monterCarte(bloc);
    var io = new IntersectionObserver(function (entrees) {
      if (entrees[0].isIntersecting) { monterCarte(bloc); io.disconnect(); }
    }, { rootMargin: '200px 0px' });
    io.observe(bloc);
  });

  /* ─── Panneau Préférences de confidentialité ─── */
  var panneau;
  function ouvrirPanneau() {
    if (!panneau) {
      panneau = document.createElement('div');
      panneau.className = 'prefs';
      panneau.setAttribute('role', 'dialog');
      panneau.setAttribute('aria-modal', 'true');
      panneau.setAttribute('aria-labelledby', 'prefs-titre');
      panneau.innerHTML =
        '<div class="prefs-boite">' +
        '<h2 id="prefs-titre">Préférences de confidentialité</h2>' +
        '<p>Ce site ne dépose aucun cookie publicitaire. La mesure d\'audience (Vercel) est anonyme et sans cookie. ' +
        'Seule la carte Google Maps fait appel à un service tiers.</p>' +
        '<label class="prefs-ligne"><span><strong>Carte Google Maps</strong><br><small>Pages Accueil et Le salon</small></span>' +
        '<input type="checkbox" id="prefs-maps"></label>' +
        '<p class="prefs-note">En savoir plus : <a href="/confidentialite">politique de confidentialité</a></p>' +
        '<div class="prefs-actions"><button type="button" class="prefs-ok">Enregistrer</button>' +
        '<button type="button" class="prefs-fermer">Fermer</button></div>' +
        '</div>';
      document.body.appendChild(panneau);
      panneau.querySelector('.prefs-fermer').addEventListener('click', fermer);
      panneau.addEventListener('click', function (e) { if (e.target === panneau) fermer(); });
      panneau.querySelector('.prefs-ok').addEventListener('click', function () {
        var avant = lire(CLE_MAPS);
        var coupe = !panneau.querySelector('#prefs-maps').checked;
        ecrire(CLE_MAPS, coupe);
        // Un script tiers déjà exécuté ne se retire pas : rechargement si l'état change
        if (avant !== coupe) location.reload(); else fermer();
      });
      document.addEventListener('keydown', function (e) { if (e.key === 'Escape') fermer(); });
    }
    panneau.querySelector('#prefs-maps').checked = !lire(CLE_MAPS);
    panneau.classList.add('ouvert');
    panneau.querySelector('#prefs-maps').focus();
  }
  function fermer() { if (panneau) panneau.classList.remove('ouvert'); }

  document.querySelectorAll('[data-prefs]').forEach(function (a) {
    a.addEventListener('click', function (e) { e.preventDefault(); ouvrirPanneau(); });
  });

  /* ─── Mesure d'audience : événements ─── */
  window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
  function evenement(nom) { window.va('event', { name: nom }); }

  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a');
    if (!a) return;
    var h = a.getAttribute('href') || '';
    var force = a.getAttribute('data-track');
    if (force) return evenement(force);
    if (h.indexOf('tel:') === 0) return evenement('tel');
    if (h.indexOf('planity.com') > -1) return evenement('reservation');
    if (h.indexOf('giftcard.sumup') > -1) return evenement('bon-cadeau');
    if (h.indexOf('instagram.com') > -1) return evenement('instagram');
    if (/maps\.apple\.com|google\.[a-z.]+\/maps|g\.page/.test(h)) return evenement(h.indexOf('/review') > -1 ? 'avis-google' : 'itineraire');
  }, true);
})();
