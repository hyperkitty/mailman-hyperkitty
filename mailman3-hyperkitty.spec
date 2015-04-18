%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

Name:           mailman3-hyperkitty
Version:        1.0
Release:        0.1.rc1%{?dist}
Summary:        Mailman archiver plugin for HyperKitty

License:        GPLv3
URL:            https://github.com/hyperkitty/mailman-hyperkitty
Source0:        https://pypi.python.org/packages/source/m/mailman-hyperkitty/mailman-hyperkitty-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  mailman
BuildRequires:  python3-requests
BuildRequires:  python3-zope-interface

Requires:       python3-setuptools
Requires:       mailman
Requires:       python3-requests
Requires:       python3-zope-interface


%description
This package contains a Mailman archiver plugin which sends emails to
HyperKitty, Mailman's web archiver.

All documentation on installing HyperKitty can be found in the documentation
provided by the HyperKitty package. It is also available online at the
following URL: http://hyperkitty.readthedocs.org.


%prep
%setup -q -n mailman-hyperkitty-%{version}


%build
%{__python3} setup.py build


%install
rm -rf $RPM_BUILD_ROOT
%{__python3} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT

# Mailman config file
install -D -m 644 mailman-hyperkitty.cfg \
    $RPM_BUILD_ROOT%{_sysconfdir}/mailman3.d/hyperkitty.cfg


%check
%{__python3} setup.py test


%files
%doc README.rst LICENSE.txt
%config %{_sysconfdir}/mailman3.d/hyperkitty.cfg
%{python3_sitelib}/*


%changelog
* Fri Mar 20 2015 Aurelien Bompard <abompard@fedoraproject.org> - 0.3
- initial package
