from setuptools import setup, find_packages

setup(
    name='unity-email-scheduler',
    version='0.1',
    packages=find_packages(where='src'),  # Tell setuptools to look for packages in 'src'
    package_dir={'': 'src'},  # Map the root package to 'src'
    install_requires=[
        # Add dependencies here, if any
        "pandas",
        "O365",
        "numpy",
        "setuptools"
    ],
    include_package_data=True,  # Include any additional files specified in MANIFEST.in
)
